"""Trendanalyse pagina — trends op de beschikbare performances."""

import streamlit as st
import pandas as pd

from src.data.processor import groepeer_per_periode, bereken_otd
from src.components.charts import trend_chart
from src.utils.constants import BESCHIKBARE_IDS, PERFORMANCE_NAMEN
from src.utils.date_utils import voeg_periode_kolommen_toe


def render_trends(df: pd.DataFrame):
    """Render trends pagina."""
    st.header("📈 Trends")

    targets = st.session_state.get("targets", {})

    # Periode keuze
    periode = st.radio("Groepeer per", ["week", "maand"], horizontal=True)

    df_t = voeg_periode_kolommen_toe(df)
    df_trend = groepeer_per_periode(df_t, periode)

    if df_trend.empty:
        st.warning("Niet genoeg data voor trendanalyse.")
        return

    # Trend chart
    fig = trend_chart(df_trend, targets, periode)
    st.plotly_chart(fig, width="stretch")

    # OTD trend
    st.subheader("On-Time Delivery Trend")
    otd_trend = df_t.groupby(periode).apply(
        lambda g: bereken_otd(g), include_groups=False
    ).reset_index(name="otd")

    if not otd_trend.empty:
        import plotly.express as px
        fig_otd = px.line(otd_trend, x=periode, y="otd",
                          title="OTD % per Periode", markers=True,
                          labels={"otd": "OTD %", periode: "Periode"})
        fig_otd.add_hline(y=95, line_dash="dash", line_color="#76a73a",
                          annotation_text="Target 95%")
        fig_otd.update_layout(yaxis_range=[0, 105])
        st.plotly_chart(fig_otd, width="stretch")

    # Data tabel
    st.subheader("📊 Data")
    display = df_trend.copy()
    for col in [c for c in display.columns if c != periode]:
        display[col] = display[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    st.dataframe(display, width="stretch", hide_index=True)
