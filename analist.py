"""OTD Analist — interactieve CLI voor OTD-analyse met LLM.

Gebruik:
    py analist.py --data "On Time Data YTD 25022026.xlsx"
    py analist.py --data data.xlsx --likp likp.xlsx

Commando's in chat:
    config     — toon huidig rekenmodel
    correctie  — sla een correctie op voor de feedback loop
    help       — overzicht commando's
    quiz       — test je OTD-kennis
    exit       — afsluiten
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings

import pandas as pd

# Onderdruk Streamlit warnings in CLI-modus
os.environ["STREAMLIT_RUNTIME"] = "0"
logging.getLogger("streamlit").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*Could not infer format.*")

# Voeg project root toe aan pad zodat src.* imports werken
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import toon_config_tekst
from src.data.processor import bereken_performances, bereken_otd, bereken_kpi_scores, root_cause_samenvatting, dedup_datagrid
from src.data.validator import valideer_datagrid, valideer_likp, kruisvalidatie
from src.data.processor import join_likp
from src.feedback_manager import bewaar_feedback, feedback_als_tekst
from src.utils.constants import PERFORMANCE_NAMEN, BESCHIKBARE_IDS


# --- LLM client (standalone, geen Streamlit) ---

def _get_llm_client():
    """Maak OpenAI client aan met OPENROUTER_API_KEY."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    from openai import OpenAI
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _get_model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")


SYSTEM_PROMPT = """Je bent een OTD-analist voor Elho B.V., een toonaangevend bedrijf in tuinproducten.
Je helpt met het analyseren van On-Time Delivery prestaties.

Het OTD-model meet 6 logistics performances in de leveringsketen:
1. Planned Performance — TMS-datum vs SAP Delivery Date
2. Capacity Performance — Bucket planning (moved/not moved)
3. Warehouse Performance — Actual GI vs Planned GI
4. Carrier Pick-up — UNDER CONSTRUCTION (geen data)
5. Carrier Departure — UNDER CONSTRUCTION (geen data)
6. Carrier Transit — POD vs TMS-datum

{rekenmodel}

{feedback}

Data-context:
{context}

Richtlijnen:
- Antwoord altijd in het Nederlands
- Geef concrete cijfers en percentages waar mogelijk
- Verwijs naar specifieke performances wanneer relevant
- Geef actionable aanbevelingen
- Wees beknopt maar volledig
- Als je iets niet kunt afleiden uit de data, zeg dat eerlijk"""


QUIZ_PROMPT = """Genereer een korte quizvraag (multiple choice, 3 opties) over OTD-concepten
of over de huidige dataset. Geef het juiste antwoord met uitleg erna.
Gebruik de data-context om relevante vragen te stellen.
Antwoord in het Nederlands."""


def _bereid_context_voor(df: pd.DataFrame) -> str:
    """Bereid data-samenvatting voor als context."""
    totaal = len(df)
    otd = bereken_otd(df)
    scores = bereken_kpi_scores(df)
    rc = root_cause_samenvatting(df)

    regels = [
        f"Totaal orders: {totaal}",
        f"Overall OTD: {otd:.1f}%",
        "",
        "Performance-scores per stap:",
    ]
    for kpi_id in BESCHIKBARE_IDS:
        score = scores.get(kpi_id)
        naam = PERFORMANCE_NAMEN.get(kpi_id, kpi_id)
        if score is not None:
            regels.append(f"  - {naam}: {score:.1f}%")
        else:
            regels.append(f"  - {naam}: geen data")

    if not rc.empty:
        regels.append("")
        regels.append("Top root causes (te late orders):")
        for _, rij in rc.head(5).iterrows():
            regels.append(f"  - {rij['root_cause_naam']}: {rij['aantal']}x ({rij['percentage']:.1f}%)")

    if "ChainName" in df.columns:
        regels.append("")
        regels.append(f"Aantal unieke klanten: {df['ChainName'].nunique()}")

    if "RequestedDeliveryDateFinal" in df.columns:
        datum_col = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        if datum_col.notna().any():
            regels.append(f"Periode: {datum_col.min().strftime('%d-%m-%Y')} t/m {datum_col.max().strftime('%d-%m-%Y')}")

    # OTD per land
    if "Country" in df.columns:
        regels.append("")
        regels.append("OTD per land:")
        for land, groep in df.groupby("Country"):
            otd_land = bereken_otd(groep)
            regels.append(f"  - {land}: {otd_land:.1f}% ({len(groep)} orders)")

    # OTD per maand
    if "RequestedDeliveryDateFinal" in df.columns:
        df_temp = df.copy()
        datum = pd.to_datetime(df_temp["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        df_temp["_maand"] = datum.dt.to_period("M").astype(str)
        valid_maand = df_temp[df_temp["_maand"].notna() & (df_temp["_maand"] != "NaT")]
        if len(valid_maand) > 0:
            regels.append("")
            regels.append("OTD per maand:")
            for maand, groep in valid_maand.groupby("_maand"):
                otd_maand = bereken_otd(groep)
                regels.append(f"  - {maand}: {otd_maand:.1f}% ({len(groep)} orders)")

    # OTD per land per maand (top-level kruistabel)
    if "Country" in df.columns and "RequestedDeliveryDateFinal" in df.columns:
        df_temp = df.copy()
        datum = pd.to_datetime(df_temp["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        df_temp["_maand"] = datum.dt.to_period("M").astype(str)
        valid = df_temp[df_temp["_maand"].notna() & (df_temp["_maand"] != "NaT")]
        if len(valid) > 0:
            regels.append("")
            regels.append("OTD per land per maand:")
            for (land, maand), groep in valid.groupby(["Country", "_maand"]):
                otd_lm = bereken_otd(groep)
                regels.append(f"  - {land} / {maand}: {otd_lm:.1f}% ({len(groep)} orders)")

    # OTD per SalesArea
    if "SalesArea" in df.columns:
        regels.append("")
        regels.append("OTD per SalesArea:")
        for area, groep in df.groupby("SalesArea"):
            otd_area = bereken_otd(groep)
            regels.append(f"  - {area}: {otd_area:.1f}% ({len(groep)} orders)")

    return "\n".join(regels)


def _stel_vraag(vraag: str, context: str, geschiedenis: list[dict]) -> str:
    """Stel een vraag aan de LLM."""
    client = _get_llm_client()
    if client is None:
        return "LLM niet beschikbaar. Stel OPENROUTER_API_KEY in als environment variabele."

    rekenmodel = toon_config_tekst()
    feedback = feedback_als_tekst()

    berichten = [
        {"role": "system", "content": SYSTEM_PROMPT.format(
            context=context,
            rekenmodel=rekenmodel,
            feedback=feedback,
        )},
    ]
    for bericht in geschiedenis[-10:]:
        berichten.append(bericht)
    berichten.append({"role": "user", "content": vraag})

    try:
        response = client.chat.completions.create(
            model=_get_model(),
            messages=berichten,
            max_tokens=1024,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Fout bij LLM-aanroep: {e}"


# --- Data laden ---

def _lees_bestand(pad: str) -> pd.DataFrame:
    """Lees een CSV of Excel bestand."""
    if pad.endswith(".csv"):
        return pd.read_csv(pad)
    else:
        return pd.read_excel(pad)


def _laad_data(data_pad: str, likp_pad: str | None = None) -> pd.DataFrame:
    """Laad en verwerk data. Met LIKP join als opgegeven."""
    df_raw = _lees_bestand(data_pad)
    df = valideer_datagrid(df_raw)
    if df is None:
        print("FOUT: Datagrid validatie mislukt.")
        sys.exit(1)

    # Dedup op DeliveryNumber (config-driven)
    n_voor = len(df)
    df = dedup_datagrid(df)
    n_na = len(df)
    if n_na < n_voor:
        print(f"Dedup: {n_voor} -> {n_na} unieke leveringen ({n_voor - n_na} duplicaten verwijderd)")

    if likp_pad:
        df_likp_raw = _lees_bestand(likp_pad)
        df_likp = valideer_likp(df_likp_raw)
        if df_likp is None:
            print("FOUT: LIKP validatie mislukt.")
            sys.exit(1)
        df, mismatches = join_likp(df, df_likp)
        if len(mismatches) > 0:
            print(f"Let op: {len(mismatches)} leveringen zonder LIKP-match.")

    df = bereken_performances(df)
    return df


# --- Commando's ---

def _cmd_config():
    """Toon huidig rekenmodel."""
    print()
    print(toon_config_tekst())
    print()


def _cmd_correctie(geschiedenis: list[dict]):
    """Sla een correctie op."""
    if len(geschiedenis) < 2:
        print("\nGeen eerdere vraag/antwoord om te corrigeren. Stel eerst een vraag.\n")
        return

    # Zoek laatste vraag/antwoord paar
    laatste_vraag = ""
    laatste_antwoord = ""
    for b in reversed(geschiedenis):
        if b["role"] == "assistant" and not laatste_antwoord:
            laatste_antwoord = b["content"]
        elif b["role"] == "user" and not laatste_vraag:
            laatste_vraag = b["content"]
        if laatste_vraag and laatste_antwoord:
            break

    print(f"\nLaatste vraag: {laatste_vraag[:80]}...")
    print(f"Laatste antwoord: {laatste_antwoord[:80]}...")
    print()
    correctie = input("Wat was er fout / wat moet anders? > ").strip()
    if not correctie:
        print("Geen correctie opgegeven.\n")
        return

    pad = bewaar_feedback(laatste_vraag, laatste_antwoord, correctie)
    print(f"Correctie opgeslagen: {pad.name}\n")


def _cmd_valideer(df: pd.DataFrame):
    """Voer kruisvalidatie uit en print resultaat."""
    print("\nKruisvalidatie Python vs PowerBI:")
    print("-" * 70)
    kv = kruisvalidatie(df)
    if kv.empty:
        print("Geen kruisvalidatie mogelijk — controleer rekenmodel.yaml configuratie.")
    else:
        for _, rij in kv.iterrows():
            py_pct = f"{rij['Python %']:.2f}%" if pd.notna(rij['Python %']) else "-"
            pb_pct = f"{rij['PowerBI kolom %']:.2f}%" if pd.notna(rij['PowerBI kolom %']) else "-"
            verschil = f"{rij['Verschil']:.2f}%" if pd.notna(rij['Verschil']) else "-"
            # Vervang emoji's door ASCII voor Windows terminal compatibiliteit
            status = rij['Status'].replace("✅", "OK").replace("⚠️", "WARN").replace("❌", "FAIL")
            print(f"  {rij['KPI']:25s}  Python: {py_pct:>8s}  PowerBI: {pb_pct:>8s}  Verschil: {verschil:>7s}  {status}")
    print()


def _cmd_help():
    """Toon beschikbare commando's."""
    print("""
Beschikbare commando's:
  config     — toon huidig rekenmodel (rekenmodel.yaml)
  correctie  — sla een correctie op voor de feedback loop
  help       — dit overzicht
  quiz       — test je OTD-kennis met een quizvraag
  valideer   — kruisvalidatie Python vs PowerBI
  exit       — afsluiten

Alles anders wordt als vraag aan de LLM gestuurd.
""")


def _cmd_quiz(context: str, geschiedenis: list[dict]):
    """Genereer een quizvraag."""
    print("\nQuizvraag wordt gegenereerd...\n")
    antwoord = _stel_vraag(QUIZ_PROMPT, context, geschiedenis)
    print(antwoord)
    print()


# --- Main loop ---

def main():
    parser = argparse.ArgumentParser(description="OTD Analist — interactieve CLI")
    parser.add_argument("--data", required=True, help="Pad naar Datagrid Excel/CSV")
    parser.add_argument("--likp", default=None, help="Optioneel: pad naar LIKP Excel/CSV")
    args = parser.parse_args()

    print("Data laden...")
    df = _laad_data(args.data, args.likp)
    print(f"{len(df)} orders geladen.\n")

    # Toon samenvatting
    otd = bereken_otd(df)
    scores = bereken_kpi_scores(df)
    print(f"OTD: {otd:.1f}%")
    for kpi_id in BESCHIKBARE_IDS:
        score = scores.get(kpi_id)
        naam = PERFORMANCE_NAMEN.get(kpi_id, kpi_id)
        if score is not None:
            print(f"  {naam}: {score:.1f}%")
    print()

    context = _bereid_context_voor(df)
    geschiedenis: list[dict] = []

    # Check LLM beschikbaarheid
    if _get_llm_client() is None:
        print("Let op: OPENROUTER_API_KEY niet ingesteld. LLM-vragen werken niet.")
        print("Commando's (config, correctie, help, quiz) werken wel.\n")

    print("Type 'help' voor beschikbare commando's, of stel een vraag.")
    print("---")

    while True:
        try:
            invoer = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTot ziens!")
            break

        if not invoer:
            continue

        cmd = invoer.lower()

        if cmd == "exit" or cmd == "quit":
            print("Tot ziens!")
            break
        elif cmd == "config":
            _cmd_config()
        elif cmd == "correctie":
            _cmd_correctie(geschiedenis)
        elif cmd == "help":
            _cmd_help()
        elif cmd == "quiz":
            _cmd_quiz(context, geschiedenis)
        elif cmd == "valideer":
            _cmd_valideer(df)
        else:
            # Vraag aan LLM
            geschiedenis.append({"role": "user", "content": invoer})
            print()
            antwoord = _stel_vraag(invoer, context, geschiedenis)
            print(antwoord)
            geschiedenis.append({"role": "assistant", "content": antwoord})


if __name__ == "__main__":
    main()
