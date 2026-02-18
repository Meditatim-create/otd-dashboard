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

    # Week-over-week delta's
    st.subheader("📊 Delta's — Week-over-week")
    st.caption("Verschil t.o.v. vorige periode: positief = verbetering, negatief = verslechtering")

    perf_cols = [c for c in df_trend.columns if c != periode]
    if len(df_trend) >= 2 and perf_cols:
        delta_df = df_trend.copy()
        for col in perf_cols:
            delta_df[f"{col}_delta"] = delta_df[col].diff()

        # Toon laatste 2 periodes als vergelijking
        laatste = delta_df.iloc[-1]
        vorige_label = delta_df.iloc[-2][periode] if len(delta_df) >= 2 else "—"
        huidige_label = laatste[periode]
        st.markdown(f"**{vorige_label}** → **{huidige_label}**")

        delta_cols = st.columns(len(perf_cols))
        for i, col in enumerate(perf_cols):
            naam = PERFORMANCE_NAMEN.get(col, col)
            waarde = laatste[col]
            delta = laatste.get(f"{col}_delta")
            with delta_cols[i]:
                if pd.notna(waarde) and pd.notna(delta):
                    st.metric(naam, f"{waarde:.1f}%", delta=f"{delta:+.1f}%")
                elif pd.notna(waarde):
                    st.metric(naam, f"{waarde:.1f}%")
                else:
                    st.metric(naam, "—")

        # OTD delta
        if not otd_trend.empty and len(otd_trend) >= 2:
            otd_nu = otd_trend.iloc[-1]["otd"]
            otd_vorig = otd_trend.iloc[-2]["otd"]
            otd_delta = otd_nu - otd_vorig
            st.metric("OTD", f"{otd_nu:.1f}%", delta=f"{otd_delta:+.1f}%")

    st.markdown("---")

    # Data tabel
    st.subheader("📊 Data")
    display = df_trend.copy()
    for col in [c for c in display.columns if c != periode]:
        display[col] = display[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    st.dataframe(display, width="stretch", hide_index=True)
