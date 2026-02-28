"""Regio pagina — OTD en performances per SalesArea."""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src.data.processor import bereken_kpi_scores, bereken_otd, groepeer_per_periode
from src.components.kpi_cards import render_kpi_kaarten, render_otd_header
from src.utils.constants import (
    BESCHIKBARE_IDS, BESCHIKBARE_STAPPEN, PERFORMANCE_NAMEN, PERFORMANCE_STAPPEN,
    ELHO_GROEN, ROOD, GRIJS, DEFAULT_TARGETS,
)
from src.utils.date_utils import voeg_periode_kolommen_toe


def render_regio(df: pd.DataFrame):
    """Render de regio-pagina met SalesArea-analyse."""
    st.header("🌍 Regio")

    if "SalesArea" not in df.columns:
        st.warning("Kolom 'SalesArea' niet gevonden in de data. Upload een Datagrid met SalesArea kolom.")
        return

    targets = st.session_state.get("targets", {})

    # --- a) KPI-kaarten per regio ---
    regio_opties = ["Alle regio's"] + sorted(df["SalesArea"].dropna().unique().tolist())
    geselecteerde_regio = st.selectbox("Selecteer regio", regio_opties)

    if geselecteerde_regio == "Alle regio's":
        df_regio = df
    else:
        df_regio = df[df["SalesArea"] == geselecteerde_regio]

    if len(df_regio) == 0:
        st.warning("Geen orders voor deze regio.")
        return

    otd = bereken_otd(df_regio)
    scores = bereken_kpi_scores(df_regio)

    render_otd_header(otd, len(df_regio))
    render_kpi_kaarten(scores, targets)

    st.markdown("---")

    # --- b) Scorecard tabel ---
    st.subheader("📇 Scorecard per regio")

    scorecard_data = []
    for regio, groep in df.groupby("SalesArea"):
        rij = {
            "SalesArea": regio,
            "Aantal": len(groep),
            "OTD %": bereken_otd(groep),
        }
        for pid in BESCHIKBARE_IDS:
            naam = PERFORMANCE_NAMEN[pid]
            if pid in groep.columns:
                valid = groep[pid].dropna()
                rij[naam] = valid.astype(float).mean() * 100 if len(valid) > 0 else None
            else:
                rij[naam] = None
        scorecard_data.append(rij)

    scorecard = pd.DataFrame(scorecard_data).sort_values("OTD %")

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

    st.markdown("---")

    # --- c) Barchart OTD per SalesArea ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("OTD per regio")
        otd_per_regio = scorecard[["SalesArea", "OTD %"]].sort_values("OTD %")

        kleuren = [ELHO_GROEN if v >= 95 else ROOD for v in otd_per_regio["OTD %"]]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=otd_per_regio["SalesArea"],
            x=otd_per_regio["OTD %"],
            orientation="h",
            marker_color=kleuren,
            text=otd_per_regio["OTD %"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
        ))
        fig_bar.add_vline(x=95, line_dash="dash", line_color=GRIJS, annotation_text="Target 95%")
        fig_bar.update_layout(
            xaxis=dict(title="OTD %", range=[0, 105]),
            height=max(300, len(otd_per_regio) * 40),
            margin=dict(l=10),
        )
        st.plotly_chart(fig_bar, width="stretch")

    # --- d) Heatmap: SalesArea x Performance ---
    with col2:
        st.subheader("Heatmap: regio x performance")

        # Bouw matrix op
        heatmap_data = []
        for _, rij in scorecard.iterrows():
            for pid in BESCHIKBARE_IDS:
                naam = PERFORMANCE_NAMEN[pid]
                heatmap_data.append({
                    "SalesArea": rij["SalesArea"],
                    "Performance": naam,
                    "Score": rij.get(naam),
                })

        heatmap_df = pd.DataFrame(heatmap_data)
        if not heatmap_df.empty:
            pivot = heatmap_df.pivot(index="SalesArea", columns="Performance", values="Score")
            # Sorteer kolommen op performance-volgorde
            col_order = [PERFORMANCE_NAMEN[pid] for pid in BESCHIKBARE_IDS if PERFORMANCE_NAMEN[pid] in pivot.columns]
            pivot = pivot[col_order]

            fig_heat = px.imshow(
                pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                color_continuous_scale=[[0, ROOD], [0.5, "#f39c12"], [1, ELHO_GROEN]],
                zmin=0, zmax=100,
                text_auto=".1f",
                aspect="auto",
            )
            fig_heat.update_layout(
                height=max(300, len(pivot) * 40),
                xaxis_title="",
                yaxis_title="",
                coloraxis_colorbar_title="%",
            )
            st.plotly_chart(fig_heat, width="stretch")

    st.markdown("---")

    # --- e) Trend per regio ---
    st.subheader("📈 OTD-trend per regio")

    periode = st.radio("Groepeer per", ["week", "maand"], horizontal=True, key="regio_periode")
    df_t = voeg_periode_kolommen_toe(df)

    # Bereken OTD per regio per periode
    trend_data = []
    for regio, groep in df_t.groupby("SalesArea"):
        for per, per_groep in groep.groupby(periode):
            trend_data.append({
                "Periode": per,
                "SalesArea": regio,
                "OTD %": bereken_otd(per_groep),
                "Aantal": len(per_groep),
            })

    if trend_data:
        trend_df = pd.DataFrame(trend_data).sort_values("Periode")

        fig_trend = px.line(
            trend_df, x="Periode", y="OTD %",
            color="SalesArea",
            markers=True,
            title=f"OTD % per {periode} per regio",
            labels={"OTD %": "OTD %", "Periode": periode.capitalize()},
        )
        fig_trend.add_hline(y=95, line_dash="dash", line_color=GRIJS, annotation_text="Target 95%")
        fig_trend.update_layout(yaxis_range=[0, 105], height=450)
        st.plotly_chart(fig_trend, width="stretch")
    else:
        st.info("Niet genoeg data voor trendanalyse per regio.")
