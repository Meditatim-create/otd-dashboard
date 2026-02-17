"""Waterval-visualisatie met Plotly."""

import plotly.graph_objects as go
import pandas as pd

from src.utils.constants import ELHO_GROEN, ELHO_DONKER, ROOD


def render_waterval(waterval_df: pd.DataFrame) -> go.Figure:
    """Maakt een waterfall chart van de performance keten."""
    if waterval_df.empty:
        return go.Figure()

    stappen = waterval_df["stap"].tolist()
    waarden = waterval_df["waarde"].tolist()
    types = waterval_df["type"].tolist()

    # Plotly waterfall measure types
    measures = []
    kleuren = []
    for t in types:
        if t == "totaal":
            measures.append("absolute")
            kleuren.append(ELHO_DONKER)
        elif t == "faal":
            measures.append("relative")
            kleuren.append(ROOD)
        else:  # ok
            measures.append("total")
            kleuren.append(ELHO_GROEN)

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=stappen,
        y=waarden,
        connector={"line": {"color": "#ccc"}},
        increasing={"marker": {"color": ELHO_GROEN}},
        decreasing={"marker": {"color": ROOD}},
        totals={"marker": {"color": ELHO_DONKER}},
        text=[abs(v) for v in waarden],
        textposition="outside",
    ))

    fig.update_layout(
        title="Performance Waterval — Waar gaat het mis?",
        yaxis_title="Aantal orders",
        showlegend=False,
        height=450,
        margin=dict(t=50, b=50),
    )

    return fig
