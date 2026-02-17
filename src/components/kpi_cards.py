"""Herbruikbare KPI-kaarten."""

import streamlit as st

from src.utils.constants import ELHO_GROEN, ROOD, KPI_IDS, KPI_NAMEN, KPI_STAPPEN


def render_kpi_kaarten(scores: dict[str, float], targets: dict[str, float]):
    """Toont 7 KPI-kaarten in een rij met groen/rood kleuring."""
    cols = st.columns(len(KPI_STAPPEN))

    for i, stap in enumerate(KPI_STAPPEN):
        kpi_id = stap["id"]
        score = scores.get(kpi_id, 0)
        target = targets.get(kpi_id, 95)
        kleur = ELHO_GROEN if score >= target else ROOD
        nummer = "①②③④⑤⑥⑦"[i]

        with cols[i]:
            st.markdown(
                f"""
                <div style="
                    background: {kleur}15;
                    border-left: 4px solid {kleur};
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                ">
                    <div style="font-size: 0.75rem; color: #666;">{nummer} {stap['naam']}</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: {kleur};">{score:.1f}%</div>
                    <div style="font-size: 0.7rem; color: #999;">Target: {target:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_otd_header(otd_pct: float, totaal_orders: int):
    """Toont de Overall OTD als grote header."""
    kleur = ELHO_GROEN if otd_pct >= 95 else ROOD
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {kleur}20, {kleur}05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <div style="font-size: 1rem; color: #666;">Overall On-Time Delivery</div>
            <div style="font-size: 3rem; font-weight: bold; color: {kleur};">{otd_pct:.1f}%</div>
            <div style="font-size: 0.85rem; color: #999;">{totaal_orders} orders in selectie</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
