"""Plotly chart wrappers."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from src.utils.constants import ELHO_GROEN, ELHO_DONKER, ROOD, KPI_NAMEN


def pareto_chart(samenvatting: pd.DataFrame) -> go.Figure:
    """Pareto chart voor root-cause analyse."""
    if samenvatting.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=samenvatting["root_cause_naam"],
        y=samenvatting["aantal"],
        name="Aantal",
        marker_color=ROOD,
        text=samenvatting["aantal"],
        textposition="outside",
    ))

    fig.add_trace(go.Scatter(
        x=samenvatting["root_cause_naam"],
        y=samenvatting["cumulatief"],
        name="Cumulatief %",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=ELHO_DONKER, width=2),
        marker=dict(size=8),
    ))

    fig.update_layout(
        title="Root-Cause Analyse — Pareto",
        yaxis=dict(title="Aantal orders"),
        yaxis2=dict(title="Cumulatief %", overlaying="y", side="right", range=[0, 105]),
        showlegend=True,
        height=400,
    )

    return fig


def kpi_barchart(scores: dict[str, float], targets: dict[str, float]) -> go.Figure:
    """Horizontale barchart met alle KPI-scores en target-lijnen."""
    namen = [KPI_NAMEN[k] for k in scores]
    waarden = list(scores.values())
    target_waarden = [targets.get(k, 95) for k in scores]
    kleuren = [ELHO_GROEN if v >= t else ROOD for v, t in zip(waarden, target_waarden)]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=namen,
        x=waarden,
        orientation="h",
        marker_color=kleuren,
        text=[f"{v:.1f}%" for v in waarden],
        textposition="outside",
        name="Score",
    ))

    # Target markers
    fig.add_trace(go.Scatter(
        y=namen,
        x=target_waarden,
        mode="markers",
        marker=dict(symbol="line-ns", size=20, color=ELHO_DONKER, line=dict(width=2)),
        name="Target",
    ))

    fig.update_layout(
        title="KPI Scores vs. Targets",
        xaxis=dict(title="%", range=[0, 105]),
        height=350,
        showlegend=True,
    )

    return fig


def trend_chart(df_trend: pd.DataFrame, targets: dict[str, float], periode_kolom: str = "week") -> go.Figure:
    """Trendlijnen per KPI over tijd."""
    if df_trend.empty:
        return go.Figure()

    fig = go.Figure()

    kleuren_lijst = ["#76a73a", "#0a4a2f", "#2ecc71", "#27ae60", "#e74c3c", "#e67e22", "#3498db"]

    for i, kpi_id in enumerate([c for c in df_trend.columns if c != periode_kolom]):
        naam = KPI_NAMEN.get(kpi_id, kpi_id)
        fig.add_trace(go.Scatter(
            x=df_trend[periode_kolom],
            y=df_trend[kpi_id],
            mode="lines+markers",
            name=naam,
            line=dict(color=kleuren_lijst[i % len(kleuren_lijst)]),
        ))

    fig.update_layout(
        title="KPI Trends over Tijd",
        xaxis_title="Periode",
        yaxis_title="%",
        yaxis=dict(range=[0, 105]),
        height=400,
    )

    return fig
