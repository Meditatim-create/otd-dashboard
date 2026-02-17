"""LLM service — Azure OpenAI of OpenRouter."""

import pandas as pd
import streamlit as st
from openai import OpenAI

from src.data.processor import bereken_kpi_scores, bereken_otd, root_cause_samenvatting
from src.utils.constants import KPI_NAMEN


SYSTEM_PROMPT = """Je bent een OTD-analist voor Elho B.V., een toonaangevend bedrijf in tuinproducten.
Je helpt management met het analyseren van On-Time Delivery prestaties.

Je hebt toegang tot de volgende data-context over de huidige dataset:
{context}

Richtlijnen:
- Antwoord altijd in het Nederlands
- Geef concrete cijfers en percentages waar mogelijk
- Verwijs naar specifieke KPI-stappen wanneer relevant (Vrijgave → TMS → Bucket → Warehouse → Ophaling → Vertrek → POD)
- Geef actionable aanbevelingen
- Wees beknopt maar volledig
- Als je iets niet kunt afleiden uit de data, zeg dat eerlijk"""


def _heeft_llm_config() -> bool:
    """Controleer of LLM secrets geconfigureerd zijn."""
    try:
        return "llm" in st.secrets and st.secrets["llm"].get("api_key")
    except Exception:
        return False


def is_beschikbaar() -> bool:
    """Controleer of de LLM service beschikbaar is."""
    return _heeft_llm_config()


def _get_client() -> OpenAI:
    """Maak OpenAI client aan op basis van configuratie."""
    config = st.secrets["llm"]
    provider = config.get("provider", "openrouter")

    if provider == "azure":
        from openai import AzureOpenAI
        return AzureOpenAI(
            api_key=config["api_key"],
            api_version=config.get("api_version", "2024-02-01"),
            azure_endpoint=config["endpoint"],
        )
    else:
        # OpenRouter (standaard)
        return OpenAI(
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://openrouter.ai/api/v1"),
        )


def _get_model() -> str:
    """Haal het model op uit config."""
    config = st.secrets["llm"]
    return config.get("model", "anthropic/claude-sonnet-4")


def bereid_context_voor(df: pd.DataFrame) -> str:
    """Bereid data-samenvatting voor als context voor de LLM."""
    totaal = len(df)
    otd = bereken_otd(df)
    scores = bereken_kpi_scores(df)
    rc = root_cause_samenvatting(df)

    regels = [
        f"Totaal orders: {totaal}",
        f"Overall OTD: {otd:.1f}%",
        "",
        "KPI-scores per stap:",
    ]
    for kpi_id, score in scores.items():
        regels.append(f"  - {KPI_NAMEN.get(kpi_id, kpi_id)}: {score:.1f}%")

    if not rc.empty:
        regels.append("")
        regels.append("Top root causes (te late orders):")
        for _, rij in rc.head(5).iterrows():
            regels.append(f"  - {rij['root_cause_naam']}: {rij['aantal']}x ({rij['percentage']:.1f}%)")

    # Klant-overzicht
    if "klant" in df.columns:
        regels.append("")
        regels.append(f"Aantal unieke klanten: {df['klant'].nunique()}")
        # Top klanten met meeste te late orders
        if "gewenste_leverdatum" in df.columns and "werkelijke_leverdatum" in df.columns:
            te_laat = df[df["werkelijke_leverdatum"] > df["gewenste_leverdatum"]]
            if not te_laat.empty:
                top_klanten = te_laat["klant"].value_counts().head(5)
                regels.append("Top klanten met te late orders:")
                for klant, aantal in top_klanten.items():
                    regels.append(f"  - {klant}: {aantal}x")

    # Periode
    if "gewenste_leverdatum" in df.columns:
        min_datum = df["gewenste_leverdatum"].min()
        max_datum = df["gewenste_leverdatum"].max()
        regels.append("")
        regels.append(f"Periode: {min_datum.strftime('%d-%m-%Y')} t/m {max_datum.strftime('%d-%m-%Y')}")

    return "\n".join(regels)


def stel_vraag(vraag: str, context: str, geschiedenis: list[dict]) -> str:
    """Stel een vraag aan de LLM met data-context en chatgeschiedenis."""
    if not _heeft_llm_config():
        return "LLM is niet geconfigureerd. Voeg API credentials toe aan `.streamlit/secrets.toml`."

    try:
        client = _get_client()
        model = _get_model()

        berichten = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        ]
        # Voeg chatgeschiedenis toe (laatste 10 berichten)
        for bericht in geschiedenis[-10:]:
            berichten.append(bericht)
        berichten.append({"role": "user", "content": vraag})

        response = client.chat.completions.create(
            model=model,
            messages=berichten,
            max_tokens=1024,
            temperature=0.3,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Fout bij het stellen van de vraag: {e}"
