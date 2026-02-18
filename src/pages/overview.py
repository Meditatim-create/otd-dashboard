"""Hoofdoverzicht met OTD, 6 performance kaarten, waterval en klant-scorecard."""

import streamlit as st
import pandas as pd

from src.data.processor import bereken_kpi_scores, bereken_otd, waterval_data, root_cause_samenvatting
from src.components.kpi_cards import render_kpi_kaarten, render_otd_header
from src.components.waterfall import render_waterval
from src.components.charts import kpi_barchart
from src.utils.constants import BESCHIKBARE_IDS, PERFORMANCE_NAMEN, ELHO_GROEN, ROOD


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

    # Klant-scorecard
    if "ChainName" in df.columns:
        st.markdown("---")
        st.subheader("📇 Klant-scorecard")
        st.caption("Alle performances per klant — rood = onder target, groen = op target")

        scorecard_data = []
        for klant, groep in df.groupby("ChainName"):
            rij = {"Klant": klant, "Aantal": len(groep), "OTD %": bereken_otd(groep)}
            for pid in BESCHIKBARE_IDS:
                naam = PERFORMANCE_NAMEN[pid]
                if pid in groep.columns:
                    valid = groep[pid].dropna()
                    rij[naam] = valid.astype(float).mean() * 100 if len(valid) > 0 else None
                else:
                    rij[naam] = None
            scorecard_data.append(rij)

        scorecard = pd.DataFrame(scorecard_data).sort_values("OTD %")
        targets = st.session_state.get("targets", {})

        # Kleur-functies voor styling
        def _kleur_pct(val):
            if pd.isna(val):
                return ""
            return f"color: {ELHO_GROEN}" if val >= 95 else f"color: {ROOD}"

        format_dict = {"OTD %": "{:.1f}%", "Aantal": "{:.0f}"}
        perf_cols = [PERFORMANCE_NAMEN[pid] for pid in BESCHIKBARE_IDS if PERFORMANCE_NAMEN[pid] in scorecard.columns]
        for col in perf_cols:
            format_dict[col] = "{:.1f}%"

        styled = scorecard.style.format(format_dict, na_rep="—")
        styled = styled.map(_kleur_pct, subset=["OTD %"] + perf_cols)
        st.dataframe(styled, width="stretch", hide_index=True)
