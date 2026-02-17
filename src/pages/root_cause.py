"""Root-cause analyse pagina."""

import streamlit as st
import pandas as pd

from src.data.processor import bereken_root_causes, root_cause_samenvatting
from src.components.charts import pareto_chart
from src.utils.constants import KPI_STAPPEN, ELHO_GROEN, ROOD


def render_root_cause(df: pd.DataFrame):
    """Render root-cause analyse pagina."""
    st.header("🔍 Root-Cause Analyse")

    te_laat = df[df["werkelijke_leverdatum"] > df["gewenste_leverdatum"]] if "werkelijke_leverdatum" in df.columns else pd.DataFrame()
    rc = bereken_root_causes(df)
    samenvatting = root_cause_samenvatting(df)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Te late orders", len(te_laat))
    col2.metric("% te laat", f"{len(te_laat) / len(df) * 100:.1f}%" if len(df) > 0 else "0%")
    top_cause = samenvatting.iloc[0]["root_cause_naam"] if not samenvatting.empty else "—"
    col3.metric("Grootste oorzaak", top_cause)

    st.markdown("---")

    # Pareto chart
    if not samenvatting.empty:
        fig = pareto_chart(samenvatting)
        st.plotly_chart(fig, use_container_width=True)

    # First-failure tabel
    st.subheader("📋 First-Failure Analyse")
    st.caption("Voor elke te late order: de eerste falende stap in de keten")

    if not rc.empty:
        # Merge met originele data voor context
        detail = df.merge(rc[["ordernummer", "root_cause_naam"]], on="ordernummer", how="inner")
        display_cols = ["ordernummer"]
        if "klant" in detail.columns:
            display_cols.append("klant")
        if "regio" in detail.columns:
            display_cols.append("regio")
        display_cols.extend(["gewenste_leverdatum", "werkelijke_leverdatum", "root_cause_naam"])
        display_cols = [c for c in display_cols if c in detail.columns]

        st.dataframe(detail[display_cols].sort_values("werkelijke_leverdatum", ascending=False),
                     use_container_width=True, hide_index=True)

        # Order detail
        st.subheader("🔎 Order Detail")
        order_lijst = detail["ordernummer"].tolist()
        geselecteerde_order = st.selectbox("Selecteer een order", order_lijst)

        if geselecteerde_order:
            order_row = df[df["ordernummer"] == geselecteerde_order].iloc[0]
            st.markdown(f"**Order: {geselecteerde_order}**")

            for stap in KPI_STAPPEN:
                kpi_id = stap["id"]
                if kpi_id in order_row.index:
                    ok = bool(order_row[kpi_id])
                    icon = "✅" if ok else "❌"
                    st.markdown(f"{icon} **{stap['naam']}** — {'OK' if ok else 'NIET OK'}")
    else:
        st.success("🎉 Geen te late orders gevonden in de huidige selectie!")
