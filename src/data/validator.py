"""Kolomvalidatie en foutmeldingen."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.constants import VERPLICHTE_KOLOMMEN, DATUM_KOLOMMEN, KPI_IDS


def valideer_kolommen(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Controleert of alle verplichte kolommen aanwezig zijn.
    Retourneert (is_valid, lijst_met_fouten).
    """
    fouten = []
    ontbrekend = [k for k in VERPLICHTE_KOLOMMEN if k not in df.columns]
    if ontbrekend:
        fouten.append(f"Ontbrekende kolommen: {', '.join(ontbrekend)}")

    return len(fouten) == 0, fouten


def converteer_datums(df: pd.DataFrame) -> pd.DataFrame:
    """Converteert datumkolommen naar datetime. Geeft waarschuwing bij fouten."""
    df = df.copy()
    for kolom in DATUM_KOLOMMEN:
        if kolom in df.columns:
            df[kolom] = pd.to_datetime(df[kolom], dayfirst=True, errors="coerce")
            n_fout = df[kolom].isna().sum()
            if n_fout > 0:
                st.warning(f"⚠️ {n_fout} rijen met ongeldig datumformaat in '{kolom}'")
    return df


def converteer_booleans(df: pd.DataFrame) -> pd.DataFrame:
    """Converteert KPI-kolommen naar boolean (0/1, ja/nee, true/false)."""
    df = df.copy()
    for kolom in KPI_IDS:
        if kolom in df.columns:
            col = df[kolom]
            if col.dtype == object:
                mapping = {"ja": True, "nee": False, "yes": True, "no": False,
                           "true": True, "false": False, "1": True, "0": False}
                df[kolom] = col.str.strip().str.lower().map(mapping)
            else:
                df[kolom] = col.astype(bool)
    return df


def valideer_en_verwerk(df: pd.DataFrame) -> pd.DataFrame | None:
    """Volledige validatie pipeline. Retourneert verwerkt DataFrame of None bij fouten."""
    is_valid, fouten = valideer_kolommen(df)
    if not is_valid:
        for fout in fouten:
            st.error(f"❌ {fout}")
        st.info(f"💡 Verwachte kolommen: {', '.join(VERPLICHTE_KOLOMMEN)}")
        return None

    df = converteer_datums(df)
    df = converteer_booleans(df)

    st.success(f"✅ {len(df)} orders geladen")
    return df
