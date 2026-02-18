"""Datum utilities voor periode-berekeningen."""

import pandas as pd
from datetime import datetime, timedelta


def week_label(datum: pd.Timestamp) -> str:
    """Geeft 'W03-2026' formaat."""
    if pd.isna(datum):
        return "Onbekend"
    return f"W{datum.isocalendar()[1]:02d}-{datum.isocalendar()[0]}"


def maand_label(datum: pd.Timestamp) -> str:
    """Geeft '2026-01' formaat."""
    if pd.isna(datum):
        return "Onbekend"
    return datum.strftime("%Y-%m")


def snelkeuze_periodes() -> dict[str, tuple[datetime, datetime]]:
    """Retourneert dict met snelkeuze-opties en hun datumranges."""
    vandaag = datetime.now().date()
    start_week = vandaag - timedelta(days=vandaag.weekday())
    start_maand = vandaag.replace(day=1)

    return {
        "Deze week": (start_week, vandaag),
        "Vorige week": (start_week - timedelta(days=7), start_week - timedelta(days=1)),
        "Deze maand": (start_maand, vandaag),
        "Vorige maand": (
            (start_maand - timedelta(days=1)).replace(day=1),
            start_maand - timedelta(days=1),
        ),
        "Laatste 30 dagen": (vandaag - timedelta(days=30), vandaag),
        "Laatste 90 dagen": (vandaag - timedelta(days=90), vandaag),
    }


def voeg_periode_kolommen_toe(df: pd.DataFrame, datumkolom: str = "RequestedDeliveryDateFinal") -> pd.DataFrame:
    """Voegt week- en maandkolommen toe aan het dataframe."""
    df = df.copy()
    if datumkolom in df.columns:
        datum = pd.to_datetime(df[datumkolom], dayfirst=True, errors="coerce")
        df["week"] = datum.apply(week_label)
        df["maand"] = datum.apply(maand_label)
    return df
