"""Detail pagina: Customer Care — PERFORMANCE_CUSTOMER_FINAL."""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.utils.constants import ELHO_GROEN, ROOD
from src.utils.date_utils import voeg_periode_kolommen_toe


def render_customer_care(df: pd.DataFrame):
    """Render Customer Care detail pagina.
    Gebruikt PERFORMANCE_CUSTOMER_FINAL uit de PowerBI data.
    """
    st.header("① Customer Care — Performance")

    perf_col = "PERFORMANCE_CUSTOMER_FINAL"
    if perf_col not in df.columns:
        st.warning(f"Kolom '{perf_col}' niet gevonden in de data.")
        return

    # Bereken score: alles dat NIET "Late" is = on time
    perf = df[perf_col].astype(str).str.strip().str.lower()
    on_time = perf != "late"
    score = on_time.mean() * 100
    target = 95.0
    n_late = (~on_time).sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Customer Performance", f"{score:.1f}%")
    col2.metric("Target", f"{target:.0f}%")
    col3.metric("Aantal Late", int(n_late))

    st.markdown("---")

    # Trend over tijd
    df_t = voeg_periode_kolommen_toe(df)
    if "week" in df_t.columns:
        df_t["_cust_ok"] = df_t[perf_col].astype(str).str.strip().str.lower() != "late"
        trend = df_t.groupby("week")["_cust_ok"].mean().reset_index()
        trend["_cust_ok"] *= 100
        fig = px.line(trend, x="week", y="_cust_ok",
                      title="Customer Performance per Week",
                      labels={"_cust_ok": "%", "week": "Week"},
                      markers=True)
        fig.add_hline(y=target, line_dash="dash", line_color=ELHO_GROEN,
                      annotation_text=f"Target {target:.0f}%")
        fig.update_layout(yaxis_range=[0, 105])
        st.plotly_chart(fig, width="stretch")

    # Top klanten met slechtste score
    if "ChainName" in df.columns:
        st.subheader("Klanten met laagste Customer Performance")
        df_calc = df.copy()
        df_calc["_cust_ok"] = df_calc[perf_col].astype(str).str.strip().str.lower() != "late"
        per_klant = df_calc.groupby("ChainName").agg(
            score=("_cust_ok", "mean"),
            aantal=("DeliveryNumber", "count"),
        ).reset_index()
        per_klant["score"] *= 100
        per_klant = per_klant.sort_values("score").head(10)
        st.dataframe(per_klant.style.format({"score": "{:.1f}%"}),
                      width="stretch", hide_index=True)

    # Uitsplitsing per land
    if "Country" in df.columns:
        st.subheader("Customer Performance per Land")
        df_calc = df.copy()
        df_calc["_cust_ok"] = df_calc[perf_col].astype(str).str.strip().str.lower() != "late"
        per_land = df_calc.groupby("Country")["_cust_ok"].mean().reset_index()
        per_land["_cust_ok"] *= 100
        fig = px.bar(per_land, x="Country", y="_cust_ok",
                     title="Customer Performance per Land",
                     color="_cust_ok",
                     color_continuous_scale=[[0, ROOD], [0.5, "#f39c12"], [1, ELHO_GROEN]])
        fig.update_layout(yaxis_range=[0, 105])
        st.plotly_chart(fig, width="stretch")
