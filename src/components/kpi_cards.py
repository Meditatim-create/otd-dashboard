"""Herbruikbare KPI-kaarten voor 6 Logistics Performances."""

import streamlit as st

from src.utils.constants import ELHO_GROEN, ROOD, GRIJS, PERFORMANCE_STAPPEN


def render_kpi_kaarten(scores: dict[str, float | None], targets: dict[str, float]):
    """Toont 6 performance-kaarten. Niet-beschikbare stappen worden grijs getoond."""
    cols = st.columns(len(PERFORMANCE_STAPPEN))
    nummers = "①②③④⑤⑥"

    for i, stap in enumerate(PERFORMANCE_STAPPEN):
        kpi_id = stap["id"]
        score = scores.get(kpi_id)
        target = targets.get(kpi_id, 95)
        nummer = nummers[i]

        with cols[i]:
            if not stap["beschikbaar"] or score is None:
                # Under construction / geen data
                st.markdown(
                    f"""
                    <div style="
                        background: {GRIJS}15;
                        border-left: 4px solid {GRIJS};
                        border-radius: 8px;
                        padding: 12px;
                        text-align: center;
                        opacity: 0.6;
                    ">
                        <div style="font-size: 0.75rem; color: #666;">{nummer} {stap['naam']}</div>
                        <div style="font-size: 1.4rem; font-weight: bold; color: {GRIJS};">🚧</div>
                        <div style="font-size: 0.65rem; color: #999;">Under construction</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                kleur = ELHO_GROEN if score >= target else ROOD
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
