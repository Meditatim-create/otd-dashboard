"""CSV/Excel upload, parsing en database-laden."""

import pandas as pd
import streamlit as st
from io import BytesIO

from src.data.database import heeft_database_config, laad_orders


def upload_bestand() -> pd.DataFrame | None:
    """Toont file uploader en retourneert DataFrame of None."""
    bestand = st.file_uploader(
        "Upload je orderdata (CSV of Excel)",
        type=["csv", "xlsx", "xls"],
        help="Upload een bestand met minimaal de verplichte kolommen. Zie het voorbeeld voor het verwachte formaat.",
    )

    if bestand is None:
        return None

    return lees_bestand(bestand)


def lees_bestand(bestand) -> pd.DataFrame:
    """Leest CSV of Excel bestand naar DataFrame."""
    naam = bestand.name.lower()
    if naam.endswith(".csv"):
        df = pd.read_csv(bestand, sep=None, engine="python")
    else:
        df = pd.read_excel(bestand)

    # Kolommen normaliseren: lowercase, strip whitespace, underscores
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    return df


def laad_uit_database() -> pd.DataFrame | None:
    """Laad data uit Supabase database."""
    if not heeft_database_config():
        return None
    return laad_orders()
