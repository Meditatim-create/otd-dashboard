"""Upload en parsing van Datagrid en LIKP bestanden."""

from __future__ import annotations

import glob
import os
import re

import pandas as pd
import streamlit as st

from src.data.database import heeft_database_config, laad_orders
from src.utils.constants import ACTION_PORTAL_PAD, ACTION_PORTAL_DATUM_KOLOMMEN


def upload_datagrid() -> pd.DataFrame | None:
    """Toont file uploader voor Datagrid (PowerBI export)."""
    bestand = st.file_uploader(
        "Datagrid (PowerBI export)",
        type=["csv", "xlsx", "xls"],
        help="PowerBI export met orderdata, performances en klantinfo (kolommen A-AL).",
        key="upload_datagrid",
    )
    if bestand is None:
        return None
    return lees_bestand(bestand)


def upload_likp() -> pd.DataFrame | None:
    """Toont file uploader voor LIKP (SAP SE16n)."""
    bestand = st.file_uploader(
        "LIKP (SAP SE16n)",
        type=["csv", "xlsx", "xls"],
        help="SAP LIKP tabel met Levering, Leveringstermijn en Pickdatum.",
        key="upload_likp",
    )
    if bestand is None:
        return None
    return lees_bestand(bestand)


def lees_bestand(bestand) -> pd.DataFrame:
    """Leest CSV of Excel bestand naar DataFrame.
    Kolomnamen worden NIET naar lowercase geconverteerd — PowerBI/SAP gebruiken CamelCase.
    Alleen whitespace wordt gestript.
    """
    naam = bestand.name.lower()
    if naam.endswith(".csv"):
        df = pd.read_csv(bestand, sep=None, engine="python")
    else:
        df = pd.read_excel(bestand)

    # Alleen whitespace strippen, geen lowercase/underscore conversie
    df.columns = df.columns.str.strip()

    return df


def laad_uit_database() -> pd.DataFrame | None:
    """Laad data uit Supabase database."""
    if not heeft_database_config():
        return None
    return laad_orders()


def laad_action_portal() -> pd.DataFrame | None:
    """Laad het nieuwste AppointmentReport bestand uit de action-portal-scraper downloads map.

    Selecteert automatisch het bestand met de meest recente datum in de bestandsnaam.
    Converteert datumkolommen en numerieke kolommen.
    """
    pattern = os.path.join(ACTION_PORTAL_PAD, "AppointmentReport_*.xlsx")
    bestanden = glob.glob(pattern)

    if not bestanden:
        return None

    # Sorteer op datum in bestandsnaam (YYYY-MM-DD)
    datum_re = re.compile(r"AppointmentReport_(\d{4}-\d{2}-\d{2})\.xlsx$")
    bestanden_met_datum = []
    for pad in bestanden:
        m = datum_re.search(os.path.basename(pad))
        if m:
            bestanden_met_datum.append((m.group(1), pad))

    if not bestanden_met_datum:
        return None

    bestanden_met_datum.sort(reverse=True)
    nieuwste_pad = bestanden_met_datum[0][1]

    df = pd.read_excel(nieuwste_pad)
    df.columns = df.columns.str.strip()

    # Datumkolommen converteren
    for kolom in ACTION_PORTAL_DATUM_KOLOMMEN:
        if kolom in df.columns:
            df[kolom] = pd.to_datetime(df[kolom], errors="coerce")

    # Numerieke kolommen converteren
    for kolom in ["Too late (min)", "Waiting (min)", "Unloading (min)", "Pallets"]:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

    # Time label opschonen (whitespace-only → NaN)
    if "Time label" in df.columns:
        df["Time label"] = df["Time label"].str.strip().replace("", pd.NA)

    # Inbound state opschonen
    if "Inbound state" in df.columns:
        df["Inbound state"] = df["Inbound state"].str.strip().replace("", pd.NA)

    return df
