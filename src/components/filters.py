"""Sidebar filters voor het dashboard."""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.utils.constants import KPI_IDS, KPI_NAMEN, DEFAULT_TARGETS
from src.utils.date_utils import snelkeuze_periodes


def init_targets():
    """Initialiseer targets in session_state."""
    if "targets" not in st.session_state:
        st.session_state.targets = DEFAULT_TARGETS.copy()


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters en retourneer gefilterd DataFrame."""
    init_targets()

    st.sidebar.header("🔍 Filters")

    # Periode filter
    st.sidebar.subheader("Periode")
    periodes = snelkeuze_periodes()
    snelkeuze = st.sidebar.selectbox("Snelkeuze", ["Aangepast"] + list(periodes.keys()))

    if snelkeuze != "Aangepast" and snelkeuze in periodes:
        start, eind = periodes[snelkeuze]
    else:
        min_datum = df["gewenste_leverdatum"].min().date() if not df["gewenste_leverdatum"].isna().all() else datetime(2024, 1, 1).date()
        max_datum = df["gewenste_leverdatum"].max().date() if not df["gewenste_leverdatum"].isna().all() else datetime.now().date()
        start = st.sidebar.date_input("Van", value=min_datum, min_value=min_datum, max_value=max_datum)
        eind = st.sidebar.date_input("Tot", value=max_datum, min_value=min_datum, max_value=max_datum)

    # Datumfilter toepassen
    mask = pd.Series(True, index=df.index)
    if "gewenste_leverdatum" in df.columns:
        mask &= df["gewenste_leverdatum"].dt.date >= start
        mask &= df["gewenste_leverdatum"].dt.date <= eind

    # Klant filter
    if "klant" in df.columns:
        klanten = sorted(df["klant"].dropna().unique())
        geselecteerde_klanten = st.sidebar.multiselect("Klant", klanten)
        if geselecteerde_klanten:
            mask &= df["klant"].isin(geselecteerde_klanten)

    # Productgroep filter
    if "productgroep" in df.columns:
        groepen = sorted(df["productgroep"].dropna().unique())
        geselecteerde_groepen = st.sidebar.multiselect("Productgroep", groepen)
        if geselecteerde_groepen:
            mask &= df["productgroep"].isin(geselecteerde_groepen)

    # Regio filter
    if "regio" in df.columns:
        regios = sorted(df["regio"].dropna().unique())
        geselecteerde_regios = st.sidebar.multiselect("Regio", regios)
        if geselecteerde_regios:
            mask &= df["regio"].isin(geselecteerde_regios)

    # Targets instellen
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Targets (%)")
    for kpi_id in KPI_IDS:
        st.session_state.targets[kpi_id] = st.sidebar.number_input(
            KPI_NAMEN[kpi_id],
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.targets[kpi_id],
            step=1.0,
            key=f"target_{kpi_id}",
        )

    return df[mask]
