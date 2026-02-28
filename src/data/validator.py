"""Validatie voor Datagrid en LIKP bestanden."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.constants import (
    VERPLICHTE_DATAGRID_KOLOMMEN,
    VERPLICHTE_LIKP_KOLOMMEN,
    DATAGRID_DATUM_KOLOMMEN,
    LIKP_DATUM_KOLOMMEN,
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
