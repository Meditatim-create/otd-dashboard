"""Root-cause analyse pagina — eerste-faal over 4 beschikbare performances."""

import streamlit as st
import pandas as pd

from src.data.processor import bereken_root_causes, root_cause_samenvatting
from src.components.charts import pareto_chart
from src.utils.constants import BESCHIKBARE_STAPPEN, PERFORMANCE_NAMEN, ELHO_GROEN, ROOD


def render_root_cause(df: pd.DataFrame):
    """Render root-cause analyse pagina."""
    st.header("🔍 Root-Cause Analyse")

    rc = bereken_root_causes(df)
    samenvatting = root_cause_samenvatting(df)

    # Metrics
    col1, col2, col3 = st.columns(3)
    te_laat_count = len(rc)
    col1.metric("Te late orders", te_laat_count)
    col2.metric("% te laat", f"{te_laat_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%")
    top_cause = samenvatting.iloc[0]["root_cause_naam"] if not samenvatting.empty else "—"
    col3.metric("Grootste oorzaak", top_cause)

    st.markdown("---")

    # Pareto chart
    if not samenvatting.empty:
        fig = pareto_chart(samenvatting)
        st.plotly_chart(fig, width="stretch")

    # First-failure tabel
    st.subheader("📋 First-Failure Analyse")
    st.caption("Voor elke te late order: de eerste falende stap in de keten (van de 4 beschikbare performances)")

    if not rc.empty:
        # Merge met originele data voor context
        detail = df.merge(rc[["DeliveryNumber", "root_cause_naam"]], on="DeliveryNumber", how="inner")
        display_cols = ["DeliveryNumber"]
        for col in ["ChainName", "Country", "Carrier", "RequestedDeliveryDateFinal",
                     "PODDeliveryDateShipment", "ReasonCodeLatesCorrected", "CommentLateOrders",
                     "root_cause_naam"]:
            if col in detail.columns:
                display_cols.append(col)

        st.dataframe(
            detail[display_cols].sort_values("PODDeliveryDateShipment", ascending=False)
            if "PODDeliveryDateShipment" in detail.columns
            else detail[display_cols],
            width="stretch", hide_index=True,
        )

        # Order detail
        st.subheader("🔎 Order Detail")
        order_lijst = detail["DeliveryNumber"].astype(str).tolist()
        geselecteerde_order = st.selectbox("Selecteer een levering", order_lijst)

        if geselecteerde_order:
            order_row = df[df["DeliveryNumber"].astype(str) == geselecteerde_order].iloc[0]
            st.markdown(f"**Levering: {geselecteerde_order}**")

            for stap in BESCHIKBARE_STAPPEN:
                kpi_id = stap["id"]
                if kpi_id in order_row.index:
                    val = order_row[kpi_id]
                    if pd.isna(val):
                        icon = "⚪"
                        status = "Geen data"
                    elif bool(val):
                        icon = "✅"
                        status = "OK"
                    else:
                        icon = "❌"
                        status = "NIET OK"
                    st.markdown(f"{icon} **{stap['naam']}** — {status}")
    else:
        st.success("🎉 Geen te late orders gevonden in de huidige selectie!")
