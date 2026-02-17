"""Detail pagina: Customer Care vrijgave performance."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.utils.constants import ELHO_GROEN, ROOD
from src.utils.date_utils import voeg_periode_kolommen_toe


def render_customer_care(df: pd.DataFrame):
    """Render Customer Care detail pagina."""
    st.header("① Customer Care — Vrijgave")

    if "vrijgave_ok" not in df.columns:
        st.warning("Kolom 'vrijgave_ok' niet gevonden in de data.")
        return

    score = df["vrijgave_ok"].mean() * 100
    target = st.session_state.get("targets", {}).get("vrijgave_ok", 95)
    kleur = ELHO_GROEN if score >= target else ROOD

    col1, col2, col3 = st.columns(3)
    col1.metric("Vrijgave Score", f"{score:.1f}%")
    col2.metric("Target", f"{target:.0f}%")
    col3.metric("Aantal niet-vrijgegeven", int((~df["vrijgave_ok"]).sum()))

    st.markdown("---")

    # Trend over tijd
    df_t = voeg_periode_kolommen_toe(df)
    if "week" in df_t.columns:
        trend = df_t.groupby("week")["vrijgave_ok"].mean().reset_index()
        trend["vrijgave_ok"] *= 100
        fig = px.line(trend, x="week", y="vrijgave_ok",
                      title="Vrijgave Performance per Week",
                      labels={"vrijgave_ok": "%", "week": "Week"},
                      markers=True)
        fig.add_hline(y=target, line_dash="dash", line_color=ELHO_GROEN,
                      annotation_text=f"Target {target:.0f}%")
        fig.update_layout(yaxis_range=[0, 105])
        st.plotly_chart(fig, use_container_width=True)

    # Top klanten met slechtste score
    if "klant" in df.columns:
        st.subheader("Klanten met laagste vrijgave-score")
        per_klant = df.groupby("klant").agg(
            score=("vrijgave_ok", "mean"),
            aantal=("ordernummer", "count"),
        ).reset_index()
        per_klant["score"] *= 100
        per_klant = per_klant.sort_values("score").head(10)
        st.dataframe(per_klant.style.format({"score": "{:.1f}%"}),
                      use_container_width=True, hide_index=True)

    # Uitsplitsing per regio
    if "regio" in df.columns:
        st.subheader("Vrijgave per Regio")
        per_regio = df.groupby("regio")["vrijgave_ok"].mean().reset_index()
        per_regio["vrijgave_ok"] *= 100
        fig = px.bar(per_regio, x="regio", y="vrijgave_ok",
                     title="Vrijgave Score per Regio",
                     color="vrijgave_ok",
                     color_continuous_scale=[[0, ROOD], [0.5, "#f39c12"], [1, ELHO_GROEN]])
        fig.update_layout(yaxis_range=[0, 105])
        st.plotly_chart(fig, use_container_width=True)
