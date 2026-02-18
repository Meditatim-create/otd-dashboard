"""Sidebar filters voor het dashboard."""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.utils.constants import BESCHIKBARE_IDS, PERFORMANCE_NAMEN, DEFAULT_TARGETS
from src.utils.date_utils import snelkeuze_periodes


def init_targets():
    """Initialiseer targets in session_state."""
    if "targets" not in st.session_state:
        st.session_state.targets = DEFAULT_TARGETS.copy()


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters en retourneer gefilterd DataFrame."""
    init_targets()

    st.sidebar.header("🔍 Filters")

    # Periode filter op RequestedDeliveryDateFinal
    datum_kolom = "RequestedDeliveryDateFinal"
    st.sidebar.subheader("Periode")
    periodes = snelkeuze_periodes()
    snelkeuze = st.sidebar.selectbox("Snelkeuze", ["Aangepast"] + list(periodes.keys()))

    if snelkeuze != "Aangepast" and snelkeuze in periodes:
        start, eind = periodes[snelkeuze]
    else:
        if datum_kolom in df.columns and not df[datum_kolom].isna().all():
            min_datum = df[datum_kolom].min().date()
            max_datum = df[datum_kolom].max().date()
        else:
            min_datum = datetime(2024, 1, 1).date()
            max_datum = datetime.now().date()
        start = st.sidebar.date_input("Van", value=min_datum, min_value=min_datum, max_value=max_datum)
        eind = st.sidebar.date_input("Tot", value=max_datum, min_value=min_datum, max_value=max_datum)

    # Datumfilter toepassen
    mask = pd.Series(True, index=df.index)
    if datum_kolom in df.columns:
        mask &= df[datum_kolom].dt.date >= start
        mask &= df[datum_kolom].dt.date <= eind

    # ChainName filter (klant)
    if "ChainName" in df.columns:
        klanten = sorted(df["ChainName"].dropna().unique())
        geselecteerde_klanten = st.sidebar.multiselect("Klant (ChainName)", klanten)
        if geselecteerde_klanten:
            mask &= df["ChainName"].isin(geselecteerde_klanten)

    # Country filter (regio)
    if "Country" in df.columns:
        landen = sorted(df["Country"].dropna().unique())
        geselecteerde_landen = st.sidebar.multiselect("Land (Country)", landen)
        if geselecteerde_landen:
            mask &= df["Country"].isin(geselecteerde_landen)

    # SalesArea filter
    if "SalesArea" in df.columns:
        areas = sorted(df["SalesArea"].dropna().astype(str).unique())
        geselecteerde_areas = st.sidebar.multiselect("SalesArea", areas)
        if geselecteerde_areas:
            mask &= df["SalesArea"].astype(str).isin(geselecteerde_areas)

    # Carrier filter
    if "Carrier" in df.columns:
        carriers = sorted(df["Carrier"].dropna().astype(str).unique())
        geselecteerde_carriers = st.sidebar.multiselect("Carrier", carriers)
        if geselecteerde_carriers:
            mask &= df["Carrier"].astype(str).isin(geselecteerde_carriers)

    # Targets instellen (alleen beschikbare performances)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Targets (%)")
    for kpi_id in BESCHIKBARE_IDS:
        st.session_state.targets[kpi_id] = st.sidebar.number_input(
            PERFORMANCE_NAMEN[kpi_id],
            min_value=0.0,
            max_value=100.0,
            value=st.session_state.targets[kpi_id],
            step=1.0,
            key=f"target_{kpi_id}",
        )

    return df[mask]
