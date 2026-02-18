"""Action Portal — Shipment appointment performance analyse."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.utils.constants import (
    ELHO_GROEN, ELHO_DONKER, ROOD, GRIJS, ORANJE,
    ACTION_TIME_LABEL_GOED, ACTION_TIME_LABEL_SLECHT,
)
from src.utils.date_utils import week_label

# Inbound states die meetellen als "onze performance"
ONZE_PERFORMANCE_STATES = ["Finished", "Cancelled", "NoShow"]
SLECHT_STATES = ["Cancelled", "NoShow"]


def render_action_portal(df: pd.DataFrame):
    """Render de Action Portal pagina."""
    st.header("Action Portal")

    if df is None or df.empty:
        st.warning("Geen Action Portal data beschikbaar.")
        return

    # Sidebar filters
    _render_action_filters(df)
    df = _pas_action_filters_toe(df)

    if df.empty:
        st.warning("Geen shipments gevonden voor de geselecteerde filters.")
        return

    # === Slot Performance ===
    # Onze performance = Finished vs Cancelled + NoShow (Refused/Removed = niet onze schuld)
    df_onze = df[df["Inbound state"].isin(ONZE_PERFORMANCE_STATES)].copy()
    totaal_onze = len(df_onze)
    finished = (df_onze["Inbound state"] == "Finished").sum()
    cancelled = (df_onze["Inbound state"] == "Cancelled").sum()
    noshow = (df_onze["Inbound state"] == "NoShow").sum()
    slot_pct = (finished / totaal_onze * 100) if totaal_onze > 0 else 0

    # Refused apart (niet onze performance)
    refused = (df["Inbound state"] == "Refused").sum()
    removed = (df["Inbound state"] == "Removed").sum()

    # OTD van finished shipments (Early + On time vs Late)
    df_finished = df_onze[df_onze["Inbound state"] == "Finished"].copy()
    df_met_label = df_finished[df_finished["Time label"].notna()].copy()
    totaal_met_label = len(df_met_label)
    op_tijd = df_met_label["Time label"].isin(ACTION_TIME_LABEL_GOED).sum() if totaal_met_label > 0 else 0
    te_laat = df_met_label["Time label"].isin(ACTION_TIME_LABEL_SLECHT).sum() if totaal_met_label > 0 else 0
    otd_pct = (op_tijd / totaal_met_label * 100) if totaal_met_label > 0 else 0

    # Toggle: Late meetellen in slot performance
    tel_late_mee = st.checkbox(
        "Late shipments ook als 'slecht' meetellen in Slot Performance",
        value=False,
        key="action_tel_late_mee",
    )

    if tel_late_mee and totaal_met_label > 0:
        # Herbereken slot performance: Finished + On time/Early vs rest
        goed_slot = op_tijd
        slecht_slot = cancelled + noshow + te_laat
        totaal_slot = goed_slot + slecht_slot
        slot_pct = (goed_slot / totaal_slot * 100) if totaal_slot > 0 else 0

    # KPI headers
    col_slot, col_otd = st.columns(2)
    with col_slot:
        _render_kpi_header("Slot Performance", slot_pct, totaal_onze,
                           "Finished vs Cancelled + NoShow" + (" + Late" if tel_late_mee else ""))
    with col_otd:
        _render_kpi_header("OTD (Finished)", otd_pct, totaal_met_label,
                           "Early + On time vs Late")

    # Metric cards
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Finished", finished)
    c2.metric("Cancelled", cancelled)
    c3.metric("NoShow", noshow)
    _metric_card_grijs(c4, "Refused", refused, "Door Action")
    _metric_card_grijs(c5, "Removed", removed, "Gepland")

    st.markdown("---")

    # Charts: DC barchart + pie chart
    col_links, col_rechts = st.columns([3, 2])

    with col_links:
        _render_dc_barchart(df_onze, tel_late_mee)

    with col_rechts:
        _render_pie_chart(df)

    st.markdown("---")

    # Trend chart
    _render_trend_chart(df_onze, tel_late_mee)

    st.markdown("---")

    # Detail tabel
    _render_detail_tabel(df)


def _render_action_filters(df: pd.DataFrame):
    """Render Action Portal specifieke sidebar filters."""
    st.sidebar.header("Action Portal Filters")

    if "DC" in df.columns:
        dcs = sorted(df["DC"].dropna().unique())
        st.sidebar.multiselect("DC (distributiecentrum)", dcs, key="action_dc_filter")

    if "Appointment" in df.columns:
        datum_vals = df["Appointment"].dropna()
        if not datum_vals.empty:
            min_d = datum_vals.min().date()
            max_d = datum_vals.max().date()
            st.sidebar.date_input("Van", value=min_d, min_value=min_d, max_value=max_d, key="action_datum_van")
            st.sidebar.date_input("Tot", value=max_d, min_value=min_d, max_value=max_d, key="action_datum_tot")


def _pas_action_filters_toe(df: pd.DataFrame) -> pd.DataFrame:
    """Pas Action Portal filters toe."""
    mask = pd.Series(True, index=df.index)

    geselecteerde_dcs = st.session_state.get("action_dc_filter", [])
    if geselecteerde_dcs:
        mask &= df["DC"].isin(geselecteerde_dcs)

    if "Appointment" in df.columns:
        datum_van = st.session_state.get("action_datum_van")
        datum_tot = st.session_state.get("action_datum_tot")
        if datum_van is not None:
            mask &= df["Appointment"].dt.date >= datum_van
        if datum_tot is not None:
            mask &= df["Appointment"].dt.date <= datum_tot

    return df[mask]


def _render_kpi_header(titel: str, pct: float, totaal: int, subtitel: str):
    """KPI header blok."""
    kleur = ELHO_GROEN if pct >= 95 else ROOD
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {kleur}20, {kleur}05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 10px;
        ">
            <div style="font-size: 1rem; color: #666;">{titel}</div>
            <div style="font-size: 3rem; font-weight: bold; color: {kleur};">{pct:.1f}%</div>
            <div style="font-size: 0.85rem; color: #999;">{totaal} shipments — {subtitel}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _metric_card_grijs(col, label: str, waarde: int, hint: str):
    """Metric in grijs — niet onze performance."""
    col.markdown(
        f"""
        <div style="
            background: {GRIJS}15;
            border-left: 4px solid {GRIJS};
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            opacity: 0.7;
        ">
            <div style="font-size: 0.75rem; color: #666;">{label}</div>
            <div style="font-size: 1.8rem; font-weight: bold; color: {GRIJS};">{waarde}</div>
            <div style="font-size: 0.65rem; color: #999;">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_dc_barchart(df: pd.DataFrame, tel_late_mee: bool):
    """Barchart: slot performance % per distributiecentrum."""
    st.subheader("Slot Performance per DC")

    if "DC" not in df.columns:
        st.info("Geen DC-data beschikbaar.")
        return

    # Groepeer per DC
    dc_groups = []
    for dc, groep in df.groupby("DC"):
        totaal = len(groep)
        finished = (groep["Inbound state"] == "Finished").sum()

        if tel_late_mee:
            # Goed = Finished + On time/Early time labels
            goed = groep["Time label"].isin(ACTION_TIME_LABEL_GOED).sum()
            slecht = totaal - goed
        else:
            goed = finished
            slecht = totaal - finished

        pct = (goed / totaal * 100) if totaal > 0 else 0
        dc_groups.append({"DC": dc, "pct": round(pct, 1), "totaal": totaal})

    dc_stats = pd.DataFrame(dc_groups).sort_values("pct", ascending=True)

    kleuren = [ELHO_GROEN if pct >= 95 else ROOD for pct in dc_stats["pct"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=dc_stats["DC"],
        x=dc_stats["pct"],
        orientation="h",
        marker_color=kleuren,
        text=[f"{v:.0f}% ({t})" for v, t in zip(dc_stats["pct"], dc_stats["totaal"])],
        textposition="outside",
    ))
    fig.add_vline(x=95, line_dash="dash", line_color=ELHO_DONKER, annotation_text="Target 95%")
    fig.update_layout(
        xaxis=dict(title="%", range=[0, 110]),
        height=max(350, len(dc_stats) * 28),
        margin=dict(l=10, r=10, t=10, b=30),
    )
    st.plotly_chart(fig, width="stretch")


def _render_pie_chart(df: pd.DataFrame):
    """Pie chart: verdeling Inbound state."""
    st.subheader("Inbound State Verdeling")

    if "Inbound state" not in df.columns:
        return

    verdeling = df["Inbound state"].value_counts().reset_index()
    verdeling.columns = ["Inbound state", "Aantal"]

    kleur_map = {
        "Finished": ELHO_GROEN,
        "Cancelled": ROOD,
        "NoShow": ORANJE,
        "Refused": GRIJS,
        "Removed": GRIJS,
    }
    kleuren = [kleur_map.get(state, GRIJS) for state in verdeling["Inbound state"]]

    fig = go.Figure(go.Pie(
        labels=verdeling["Inbound state"],
        values=verdeling["Aantal"],
        marker=dict(colors=kleuren),
        textinfo="label+percent+value",
        hole=0.3,
    ))
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")


def _render_trend_chart(df: pd.DataFrame, tel_late_mee: bool):
    """Trend chart: slot performance % per week."""
    st.subheader("Slot Performance Trend per Week")

    if "Appointment" not in df.columns:
        st.info("Geen trenddata beschikbaar.")
        return

    df_trend = df.copy()
    df_trend["week"] = df_trend["Appointment"].apply(week_label)
    df_trend = df_trend[df_trend["week"] != "Onbekend"]

    if df_trend.empty:
        st.info("Geen geldige datums voor trendberekening.")
        return

    # Groepeer per week
    trend_groups = []
    for week, groep in df_trend.groupby("week"):
        totaal = len(groep)
        if tel_late_mee:
            goed = groep["Time label"].isin(ACTION_TIME_LABEL_GOED).sum()
        else:
            goed = (groep["Inbound state"] == "Finished").sum()
        pct = (goed / totaal * 100) if totaal > 0 else 0
        trend_groups.append({"week": week, "pct": round(pct, 1), "totaal": totaal})

    trend = pd.DataFrame(trend_groups).sort_values("week")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["week"],
        y=trend["pct"],
        mode="lines+markers",
        name="Slot Performance %",
        line=dict(color=ELHO_GROEN, width=2),
        marker=dict(size=8),
        text=[f"{t} shipments" for t in trend["totaal"]],
        hovertemplate="%{x}<br>%{y:.1f}%<br>%{text}<extra></extra>",
    ))
    fig.add_hline(y=95, line_dash="dash", line_color=ROOD, annotation_text="Target 95%")
    fig.update_layout(
        xaxis_title="Week",
        yaxis_title="%",
        yaxis=dict(range=[0, 105]),
        height=400,
    )
    st.plotly_chart(fig, width="stretch")


def _render_detail_tabel(df: pd.DataFrame):
    """Volledige shipment data tabel."""
    st.subheader("Alle Shipments")

    toon_kolommen = [
        "Owner", "Ship ID", "PO NO", "DC", "Inbound state",
        "Appointment", "Time label", "Arrival",
        "Too late (min)", "Pallets", "Zone",
    ]
    beschikbaar = [k for k in toon_kolommen if k in df.columns]

    st.dataframe(
        df[beschikbaar].sort_values("Appointment", ascending=False, na_position="last"),
        width="stretch",
        hide_index=True,
        height=500,
    )
