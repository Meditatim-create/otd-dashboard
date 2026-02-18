"""Hoofdoverzicht met OTD, 6 performance kaarten en waterval."""

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

    # 6 Performance kaarten (inclusief under construction)
    render_kpi_kaarten(scores, targets)

    st.markdown("---")

    # Waterval en barchart naast elkaar
    col1, col2 = st.columns([3, 2])

    with col1:
        wv = waterval_data(df)
        fig = render_waterval(wv)
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig2 = kpi_barchart(scores, targets)
        st.plotly_chart(fig2, width="stretch")

    # Samenvatting
    st.subheader("📋 Samenvatting")
    col_a, col_b, col_c = st.columns(3)

    # OTD berekening: POD <= RequestedDeliveryDateFinal
    if "PODDeliveryDateShipment" in df.columns and "RequestedDeliveryDateFinal" in df.columns:
        pod = pd.to_datetime(df["PODDeliveryDateShipment"], dayfirst=True, errors="coerce")
        req = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        valid = pod.notna() & req.notna()
        te_laat_count = (pod[valid] > req[valid]).sum()
        op_tijd_count = valid.sum() - te_laat_count
    else:
        te_laat_count = 0
        op_tijd_count = 0

    col_a.metric("Totaal orders", len(df))
    col_b.metric("Op tijd", op_tijd_count)
    col_c.metric("Te laat", te_laat_count)

    # Top root causes
    rc = root_cause_samenvatting(df)
    if not rc.empty:
        st.subheader("🔍 Top Root Causes")
        st.dataframe(rc, width="stretch", hide_index=True)
