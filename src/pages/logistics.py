"""Detail pagina: 6 logistieke KPI's."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.utils.constants import KPI_STAPPEN, KPI_NAMEN, ELHO_GROEN, ROOD
from src.data.processor import bereken_kpi_scores


def render_logistics(df: pd.DataFrame):
    """Render Logistiek detail pagina."""
    st.header("🚛 Logistiek — Detail")

    logistiek_stappen = [s for s in KPI_STAPPEN if s["afdeling"] == "Logistiek"]
    scores = bereken_kpi_scores(df)
    targets = st.session_state.get("targets", {})

    # KPI kaarten voor logistiek
    cols = st.columns(len(logistiek_stappen))
    for i, stap in enumerate(logistiek_stappen):
        kpi_id = stap["id"]
        score = scores.get(kpi_id, 0)
        target = targets.get(kpi_id, 95)
        kleur = ELHO_GROEN if score >= target else ROOD
        with cols[i]:
            st.metric(f"{stap['naam']}", f"{score:.1f}%",
                      delta=f"{score - target:+.1f}%" if target else None)

    st.markdown("---")

    # Vergelijking barchart
    namen = [s["naam"] for s in logistiek_stappen]
    waarden = [scores.get(s["id"], 0) for s in logistiek_stappen]
    target_waarden = [targets.get(s["id"], 95) for s in logistiek_stappen]
    kleuren = [ELHO_GROEN if v >= t else ROOD for v, t in zip(waarden, target_waarden)]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=namen, y=waarden, marker_color=kleuren,
                         text=[f"{v:.1f}%" for v in waarden], textposition="outside"))
    for naam, t in zip(namen, target_waarden):
        fig.add_shape(type="line", x0=naam, x1=naam, y0=t - 1, y1=t + 1,
                      line=dict(color="black", width=3))

    fig.update_layout(title="Logistieke KPI's — Vergelijking",
                      yaxis=dict(title="%", range=[0, 105]), height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Detail per stap
    st.subheader("Detail per Stap")
    geselecteerde_stap = st.selectbox("Kies een stap",
                                       [s["naam"] for s in logistiek_stappen])
    stap_info = next(s for s in logistiek_stappen if s["naam"] == geselecteerde_stap)
    kpi_id = stap_info["id"]

    if kpi_id in df.columns:
        col1, col2 = st.columns(2)

        with col1:
            # Per klant
            if "klant" in df.columns:
                per_klant = df.groupby("klant")[kpi_id].agg(["mean", "count"]).reset_index()
                per_klant.columns = ["klant", "score", "aantal"]
                per_klant["score"] *= 100
                per_klant = per_klant.sort_values("score").head(10)
                st.markdown(f"**Laagste {geselecteerde_stap}-score per klant**")
                st.dataframe(per_klant.style.format({"score": "{:.1f}%"}),
                             use_container_width=True, hide_index=True)

        with col2:
            # Per regio
            if "regio" in df.columns:
                per_regio = df.groupby("regio")[kpi_id].agg(["mean", "count"]).reset_index()
                per_regio.columns = ["regio", "score", "aantal"]
                per_regio["score"] *= 100
                per_regio = per_regio.sort_values("score")
                st.markdown(f"**{geselecteerde_stap}-score per regio**")
                st.dataframe(per_regio.style.format({"score": "{:.1f}%"}),
                             use_container_width=True, hide_index=True)
