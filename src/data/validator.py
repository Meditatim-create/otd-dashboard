"""Validatie voor Datagrid en LIKP bestanden + kruisvalidatie & data quality."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.utils.constants import (
    VERPLICHTE_DATAGRID_KOLOMMEN,
    VERPLICHTE_LIKP_KOLOMMEN,
    DATAGRID_DATUM_KOLOMMEN,
    LIKP_DATUM_KOLOMMEN,
    BESCHIKBARE_IDS,
    PERFORMANCE_NAMEN,
)


def _zoek_kolom(df: pd.DataFrame, naam: str) -> str | None:
    """Zoek kolom case-insensitive. Retourneert originele kolomnaam of None."""
    naam_lower = naam.lower()
    for kolom in df.columns:
        if kolom.lower() == naam_lower:
            return kolom
    return None


def _valideer_kolommen(df: pd.DataFrame, verplicht: list[str], bron: str) -> tuple[bool, list[str]]:
    """Controleert of verplichte kolommen aanwezig zijn (case-insensitive).
    Retourneert (is_valid, lijst_met_fouten).
    """
    fouten = []
    ontbrekend = []
    for kolom in verplicht:
        if _zoek_kolom(df, kolom) is None:
            ontbrekend.append(kolom)
    if ontbrekend:
        fouten.append(f"{bron}: ontbrekende kolommen: {', '.join(ontbrekend)}")
    return len(fouten) == 0, fouten


def _converteer_datums(df: pd.DataFrame, datum_kolommen: list[str]) -> pd.DataFrame:
    """Converteert datumkolommen naar datetime (case-insensitive lookup)."""
    df = df.copy()
    for kolom_naam in datum_kolommen:
        kolom = _zoek_kolom(df, kolom_naam)
        if kolom is not None:
            df[kolom] = pd.to_datetime(df[kolom], dayfirst=True, errors="coerce")
            n_fout = df[kolom].isna().sum()
            if n_fout > 0:
                st.warning(f"⚠️ {n_fout} rijen met ongeldig datumformaat in '{kolom}'")
    return df


def valideer_datagrid(df: pd.DataFrame) -> pd.DataFrame | None:
    """Valideer en verwerk Datagrid (PowerBI export)."""
    is_valid, fouten = _valideer_kolommen(df, VERPLICHTE_DATAGRID_KOLOMMEN, "Datagrid")
    if not is_valid:
        for fout in fouten:
            st.error(f"❌ {fout}")
        st.info(f"💡 Verwachte kolommen: {', '.join(VERPLICHTE_DATAGRID_KOLOMMEN)}")
        return None

    df = _converteer_datums(df, DATAGRID_DATUM_KOLOMMEN)
    st.success(f"✅ Datagrid: {len(df)} orders geladen")
    return df


def valideer_likp(df: pd.DataFrame) -> pd.DataFrame | None:
    """Valideer en verwerk LIKP (SAP SE16n)."""
    # Normaliseer bekende kolomnaam-varianten vóór validatie
    from src.data.processor import _normaliseer_likp_kolommen
    df = _normaliseer_likp_kolommen(df)

    is_valid, fouten = _valideer_kolommen(df, VERPLICHTE_LIKP_KOLOMMEN, "LIKP")
    if not is_valid:
        for fout in fouten:
            st.error(f"❌ {fout}")
        st.info(f"💡 Verwachte kolommen: {', '.join(VERPLICHTE_LIKP_KOLOMMEN)}")
        return None

    df = _converteer_datums(df, LIKP_DATUM_KOLOMMEN)
    st.success(f"✅ LIKP: {len(df)} leveringen geladen")
    return df


# --- Kruisvalidatie & Data Quality ---

def kruisvalidatie(df: pd.DataFrame) -> pd.DataFrame:
    """Vergelijk Python-berekende KPI's met PowerBI-bronkolommen.

    Retourneert een DataFrame met per KPI:
    - kpi_naam, python_pct, powerbi_pct, verschil, status (✅/⚠️/❌)
    """
    from src.config import get_performance_config, get_otd_config
    from src.data.processor import bereken_otd

    resultaten = []

    # OTD kruisvalidatie
    otd_cfg = get_otd_config()
    python_otd = bereken_otd(df)
    if otd_cfg.get("method") == "column":
        src_col = otd_cfg.get("source_column", "")
        if src_col in df.columns:
            ok_vals = [v.lower() for v in otd_cfg.get("ok_values", [])]
            no_pod_vals = [v.lower() for v in otd_cfg.get("no_pod_values", [])]
            col = df[src_col].astype(str).str.strip().str.lower()
            if no_pod_vals:
                mask = ~col.isin(no_pod_vals) & df[src_col].notna()
            else:
                mask = df[src_col].notna()
            valid = col[mask]
            powerbi_otd = (valid.isin(ok_vals).sum() / len(valid) * 100) if len(valid) > 0 else 0.0
            verschil = abs(python_otd - powerbi_otd)
            resultaten.append({
                "KPI": "OTD",
                "Python %": round(python_otd, 2),
                "PowerBI kolom %": round(powerbi_otd, 2),
                "Verschil": round(verschil, 2),
                "Status": _validatie_status(verschil),
            })

    # Per performance-stap
    for kpi_id in BESCHIKBARE_IDS:
        cfg = get_performance_config(kpi_id)
        naam = PERFORMANCE_NAMEN.get(kpi_id, kpi_id)

        # Python-berekend percentage
        if kpi_id in df.columns:
            valid_py = df[kpi_id].dropna()
            python_pct = valid_py.astype(float).mean() * 100 if len(valid_py) > 0 else None
        else:
            python_pct = None

        # PowerBI-bronkolom percentage (alleen bij method=column)
        powerbi_pct = None
        if cfg.get("method") == "column":
            src_col = cfg.get("source_column", "")
            if src_col in df.columns:
                ok_vals = [v.lower() for v in cfg.get("ok_values", [])]
                no_pod_vals = [v.lower() for v in cfg.get("no_pod_values", [])]
                col = df[src_col].astype(str).str.strip().str.lower()
                niet_leeg = df[src_col].notna()
                if no_pod_vals:
                    niet_leeg = niet_leeg & ~col.isin(no_pod_vals)
                valid_pb = col[niet_leeg]
                powerbi_pct = (valid_pb.isin(ok_vals).sum() / len(valid_pb) * 100) if len(valid_pb) > 0 else None

        if python_pct is not None and powerbi_pct is not None:
            verschil = abs(python_pct - powerbi_pct)
            status = _validatie_status(verschil)
        elif python_pct is not None:
            verschil = None
            status = "— (geen bronkolom)"
        else:
            verschil = None
            status = "— (geen data)"

        resultaten.append({
            "KPI": naam,
            "Python %": round(python_pct, 2) if python_pct is not None else None,
            "PowerBI kolom %": round(powerbi_pct, 2) if powerbi_pct is not None else None,
            "Verschil": round(verschil, 2) if verschil is not None else None,
            "Status": status,
        })

    return pd.DataFrame(resultaten)


def _validatie_status(verschil: float) -> str:
    """Bepaal status-icoon op basis van verschil."""
    if verschil < 0.5:
        return "✅"
    elif verschil < 2.0:
        return "⚠️"
    else:
        return "❌"


def data_quality_rapport(df: pd.DataFrame) -> dict:
    """Genereer een data quality rapport.

    Retourneert dict met:
    - missing: dict[kolom] -> {count, pct}
    - duplicaten: {voor_dedup, na_dedup, verwijderd}
    - no_pod: {count, pct}
    - nan_performances: dict[kpi_id] -> {count, pct}
    """
    from src.config import get_otd_config

    totaal = len(df)

    # Missing values per verplichte kolom
    verplicht = VERPLICHTE_DATAGRID_KOLOMMEN + ["Leveringstermijn", "Pickdatum"]
    missing = {}
    for kolom in verplicht:
        if kolom in df.columns:
            n_miss = df[kolom].isna().sum()
            missing[kolom] = {"count": int(n_miss), "pct": round(n_miss / totaal * 100, 1) if totaal > 0 else 0}

    # Duplicaten check
    if "DeliveryNumber" in df.columns:
        n_uniek = df["DeliveryNumber"].nunique()
        n_dupl = totaal - n_uniek
    else:
        n_uniek = totaal
        n_dupl = 0
    duplicaten = {"totaal": totaal, "uniek": n_uniek, "duplicaten": n_dupl}

    # NO POD telling
    no_pod = {"count": 0, "pct": 0.0}
    otd_cfg = get_otd_config()
    if otd_cfg.get("method") == "column":
        src_col = otd_cfg.get("source_column", "")
        no_pod_vals = [v.lower() for v in otd_cfg.get("no_pod_values", [])]
        if src_col in df.columns and no_pod_vals:
            col = df[src_col].astype(str).str.strip().str.lower()
            n_no_pod = col.isin(no_pod_vals).sum()
            no_pod = {"count": int(n_no_pod), "pct": round(n_no_pod / totaal * 100, 1) if totaal > 0 else 0}

    # NaN in performance-kolommen
    nan_performances = {}
    for kpi_id in BESCHIKBARE_IDS:
        if kpi_id in df.columns:
            n_nan = df[kpi_id].isna().sum()
            nan_performances[kpi_id] = {
                "naam": PERFORMANCE_NAMEN.get(kpi_id, kpi_id),
                "count": int(n_nan),
                "pct": round(n_nan / totaal * 100, 1) if totaal > 0 else 0,
            }

    return {
        "totaal_orders": totaal,
        "missing": missing,
        "duplicaten": duplicaten,
        "no_pod": no_pod,
        "nan_performances": nan_performances,
    }


def reconciliatie_data(df: pd.DataFrame) -> pd.DataFrame:
    """Maak per-order vergelijking Python vs PowerBI voor elke KPI.

    Retourneert DataFrame met DeliveryNumber + per KPI: python_bool, powerbi_waarde.
    """
    from src.config import get_performance_config, get_otd_config

    result = df[["DeliveryNumber"]].copy() if "DeliveryNumber" in df.columns else pd.DataFrame(index=df.index)

    # OTD
    otd_cfg = get_otd_config()
    if "otd_ok" in df.columns:
        result["OTD_python"] = df["otd_ok"]
    if otd_cfg.get("method") == "column":
        src_col = otd_cfg.get("source_column", "")
        if src_col in df.columns:
            result[f"OTD_powerbi ({src_col})"] = df[src_col]

    # Per performance
    for kpi_id in BESCHIKBARE_IDS:
        naam = PERFORMANCE_NAMEN.get(kpi_id, kpi_id)
        if kpi_id in df.columns:
            result[f"{naam}_python"] = df[kpi_id]
        cfg = get_performance_config(kpi_id)
        if cfg.get("method") == "column":
            src_col = cfg.get("source_column", "")
            if src_col in df.columns:
                result[f"{naam}_powerbi ({src_col})"] = df[src_col]

    return result
