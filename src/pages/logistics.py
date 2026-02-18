"""Detail pagina: 6 Logistics Performances."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.utils.constants import (
    PERFORMANCE_STAPPEN, PERFORMANCE_NAMEN, BESCHIKBARE_STAPPEN,
    ELHO_GROEN, ROOD, GRIJS,
)
from src.data.processor import bereken_kpi_scores


def render_logistics(df: pd.DataFrame):
    """Render Logistiek detail pagina met 6 performances."""
    st.header("🚛 Logistiek — 6 Performances")

    scores = bereken_kpi_scores(df)
    targets = st.session_state.get("targets", {})

    # KPI kaarten — alle 6
    cols = st.columns(len(PERFORMANCE_STAPPEN))
    nummers = "①②③④⑤⑥"
    for i, stap in enumerate(PERFORMANCE_STAPPEN):
        kpi_id = stap["id"]
        score = scores.get(kpi_id)
        target = targets.get(kpi_id, 95)
        with cols[i]:
            if not stap["beschikbaar"] or score is None:
                st.metric(f"{nummers[i]} {stap['naam']}", "🚧",
                          help="Under construction — geen data beschikbaar")
            else:
                delta = f"{score - target:+.1f}%" if target else None
                st.metric(f"{nummers[i]} {stap['naam']}", f"{score:.1f}%", delta=delta)

    st.markdown("---")

    # Vergelijking barchart (alleen beschikbare)
    namen = []
    waarden = []
    target_waarden = []
    for stap in BESCHIKBARE_STAPPEN:
        score = scores.get(stap["id"])
        if score is None:
            continue
        namen.append(stap["naam"])
        waarden.append(score)
        target_waarden.append(targets.get(stap["id"], 95))

    if namen:
        kleuren = [ELHO_GROEN if v >= t else ROOD for v, t in zip(waarden, target_waarden)]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=namen, y=waarden, marker_color=kleuren,
                             text=[f"{v:.1f}%" for v in waarden], textposition="outside"))
        for naam, t in zip(namen, target_waarden):
            fig.add_shape(type="line", x0=naam, x1=naam, y0=t - 1, y1=t + 1,
                          line=dict(color="black", width=3))
        fig.update_layout(title="Logistics Performances — Vergelijking",
                          yaxis=dict(title="%", range=[0, 105]), height=400)
        st.plotly_chart(fig, width="stretch")

    # Detail per beschikbare stap
    st.subheader("Detail per Performance")
    beschikbare_namen = [s["naam"] for s in BESCHIKBARE_STAPPEN]
    geselecteerde_stap = st.selectbox("Kies een performance", beschikbare_namen)
    stap_info = next(s for s in BESCHIKBARE_STAPPEN if s["naam"] == geselecteerde_stap)
    kpi_id = stap_info["id"]

    if kpi_id in df.columns:
        col1, col2 = st.columns(2)

        with col1:
            # Per klant (ChainName)
            if "ChainName" in df.columns:
                df_valid = df[df[kpi_id].notna()].copy()
                df_valid[kpi_id] = df_valid[kpi_id].astype(float)
                per_klant = df_valid.groupby("ChainName")[kpi_id].agg(["mean", "count"]).reset_index()
                per_klant.columns = ["ChainName", "score", "aantal"]
                per_klant["score"] *= 100
                per_klant = per_klant.sort_values("score").head(10)
                st.markdown(f"**Laagste {geselecteerde_stap}-score per klant**")
                st.dataframe(per_klant.style.format({"score": "{:.1f}%"}),
                             width="stretch", hide_index=True)

        with col2:
            # Per land (Country)
            if "Country" in df.columns:
                df_valid = df[df[kpi_id].notna()].copy()
                df_valid[kpi_id] = df_valid[kpi_id].astype(float)
                per_land = df_valid.groupby("Country")[kpi_id].agg(["mean", "count"]).reset_index()
                per_land.columns = ["Country", "score", "aantal"]
                per_land["score"] *= 100
                per_land = per_land.sort_values("score")
                st.markdown(f"**{geselecteerde_stap}-score per land**")
                st.dataframe(per_land.style.format({"score": "{:.1f}%"}),
                             width="stretch", hide_index=True)
