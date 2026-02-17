"""Hoofdoverzicht met waterval + KPI-kaarten."""

import streamlit as st
import pandas as pd

from src.data.processor import bereken_kpi_scores, bereken_otd, waterval_data, root_cause_samenvatting
from src.components.kpi_cards import render_kpi_kaarten, render_otd_header
from src.components.waterfall import render_waterval
from src.components.charts import kpi_barchart


def render_overview(df: pd.DataFrame):
    """Render de overview pagina."""
    st.header("📊 Overzicht")

    scores = bereken_kpi_scores(df)
    otd = bereken_otd(df)
    targets = st.session_state.get("targets", {})

    # OTD header
    render_otd_header(otd, len(df))

    # KPI kaarten
    render_kpi_kaarten(scores, targets)

    st.markdown("---")

    # Waterval en barchart naast elkaar
    col1, col2 = st.columns([3, 2])

    with col1:
        wv = waterval_data(df)
        fig = render_waterval(wv)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = kpi_barchart(scores, targets)
        st.plotly_chart(fig2, use_container_width=True)

    # Samenvatting
    st.subheader("📋 Samenvatting")
    col_a, col_b, col_c = st.columns(3)

    te_laat = df[df["werkelijke_leverdatum"] > df["gewenste_leverdatum"]] if "werkelijke_leverdatum" in df.columns else pd.DataFrame()
    col_a.metric("Totaal orders", len(df))
    col_b.metric("Op tijd", len(df) - len(te_laat))
    col_c.metric("Te laat", len(te_laat))

    # Top root causes
    rc = root_cause_samenvatting(df)
    if not rc.empty:
        st.subheader("🔍 Top Root Causes")
        st.dataframe(rc, use_container_width=True, hide_index=True)
