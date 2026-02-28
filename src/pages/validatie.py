"""Validatie pagina — automatische controle Python vs PowerBI."""

from io import BytesIO

import pandas as pd
import streamlit as st

from src.data.validator import kruisvalidatie, data_quality_rapport, reconciliatie_data
from src.utils.constants import ELHO_GROEN, ROOD, ORANJE, BESCHIKBARE_IDS, PERFORMANCE_NAMEN


def render_validatie(df: pd.DataFrame):
    """Render de validatie-pagina."""
    st.header("🔍 Validatie")
    st.caption("Automatische controle dat Python-berekeningen overeenkomen met PowerBI")

    # --- a) Kruisvalidatie Python vs PowerBI ---
    st.subheader("Kruisvalidatie Python vs PowerBI")

    kv = kruisvalidatie(df)
    if kv.empty:
        st.info("Geen kruisvalidatie mogelijk — controleer rekenmodel.yaml configuratie.")
    else:
        # Kleur status-kolom
        def _kleur_status(val):
            if "✅" in str(val):
                return f"color: {ELHO_GROEN}; font-weight: bold"
            elif "⚠️" in str(val):
                return f"color: {ORANJE}; font-weight: bold"
            elif "❌" in str(val):
                return f"color: {ROOD}; font-weight: bold"
            return ""

        styled = kv.style.format(
            {"Python %": "{:.2f}%", "PowerBI kolom %": "{:.2f}%", "Verschil": "{:.2f}%"},
            na_rep="—",
        ).map(_kleur_status, subset=["Status"])

        st.dataframe(styled, width="stretch", hide_index=True)

        # Samenvatting
        n_ok = kv["Status"].str.contains("✅", na=False).sum()
        n_warn = kv["Status"].str.contains("⚠️", na=False).sum()
        n_fail = kv["Status"].str.contains("❌", na=False).sum()
        if n_fail > 0:
            st.error(f"❌ {n_fail} KPI's wijken significant af (> 2%)")
        elif n_warn > 0:
            st.warning(f"⚠️ {n_warn} KPI's wijken licht af (0.5-2%)")
        else:
            st.success(f"✅ Alle {n_ok} KPI's valideren — Python en PowerBI zijn in sync")

    st.markdown("---")

    # --- b) Data Quality ---
    st.subheader("Data Quality")

    dq = data_quality_rapport(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Totaal orders", f"{dq['totaal_orders']:,}")
    col2.metric("NO POD", f"{dq['no_pod']['count']:,}", delta=f"{dq['no_pod']['pct']:.1f}%", delta_color="inverse")
    col3.metric("Duplicaten", f"{dq['duplicaten']['duplicaten']:,}",
                help=f"{dq['duplicaten']['uniek']:,} uniek van {dq['duplicaten']['totaal']:,}")

    # Missing values tabel
    st.markdown("**Missing values per verplichte kolom**")
    missing_data = []
    for kolom, info in dq["missing"].items():
        if info["count"] > 0:
            missing_data.append({"Kolom": kolom, "Missend": info["count"], "%": f"{info['pct']:.1f}%"})
    if missing_data:
        st.dataframe(pd.DataFrame(missing_data), width="stretch", hide_index=True)
    else:
        st.success("Geen missing values in verplichte kolommen")

    # NaN in performance-kolommen
    st.markdown("**NaN in performance-kolommen**")
    nan_data = []
    for kpi_id, info in dq["nan_performances"].items():
        nan_data.append({"Performance": info["naam"], "NaN": info["count"], "%": f"{info['pct']:.1f}%"})
    if nan_data:
        st.dataframe(pd.DataFrame(nan_data), width="stretch", hide_index=True)

    st.markdown("---")

    # --- c) Data Freshness ---
    st.subheader("Data Freshness")

    if "RequestedDeliveryDateFinal" in df.columns:
        datum = pd.to_datetime(df["RequestedDeliveryDateFinal"], dayfirst=True, errors="coerce")
        datum_valid = datum.dropna()

        if len(datum_valid) > 0:
            oudste = datum_valid.min()
            nieuwste = datum_valid.max()
            vandaag = pd.Timestamp.now()
            dagen_oud = (vandaag - nieuwste).days

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Oudste order", oudste.strftime("%d-%m-%Y"))
            col_b.metric("Nieuwste order", nieuwste.strftime("%d-%m-%Y"))
            col_c.metric("Data-leeftijd", f"{dagen_oud} dagen")

            if dagen_oud > 7:
                st.warning(f"⚠️ Nieuwste data is {dagen_oud} dagen oud — mogelijk niet actueel")

            # Mini-histogram: orders per week
            st.markdown("**Orders per week**")
            df_temp = df.copy()
            df_temp["_week"] = datum.dt.isocalendar().week.astype(str).str.zfill(2)
            df_temp["_jaar"] = datum.dt.isocalendar().year.astype(str)
            df_temp["_weeklabel"] = "W" + df_temp["_week"] + "-" + df_temp["_jaar"]

            # Sorteer op jaar+week
            week_counts = df_temp.dropna(subset=["_weeklabel"]).groupby("_weeklabel").size().reset_index(name="Aantal")
            week_counts = week_counts.sort_values("_weeklabel")

            import plotly.express as px
            fig = px.bar(
                week_counts.tail(20),  # laatste 20 weken
                x="_weeklabel", y="Aantal",
                title="Orders per week (laatste 20 weken)",
                labels={"_weeklabel": "Week", "Aantal": "Orders"},
                color_discrete_sequence=[ELHO_GROEN],
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Kolom 'RequestedDeliveryDateFinal' niet gevonden — freshness check niet mogelijk.")

    st.markdown("---")

    # --- d) Reconciliatie Export ---
    st.subheader("Reconciliatie Export")
    st.caption("Download per-order vergelijking: Python-berekening vs PowerBI-waarde voor elke KPI")

    recon = reconciliatie_data(df)

    def _maak_recon_excel(recon_df: pd.DataFrame, kv_df: pd.DataFrame, dq_dict: dict) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            recon_df.to_excel(writer, index=False, sheet_name="Per Order")
            kv_df.to_excel(writer, index=False, sheet_name="Kruisvalidatie")
            # Data quality sheet
            dq_rows = []
            dq_rows.append({"Metric": "Totaal orders", "Waarde": dq_dict["totaal_orders"]})
            dq_rows.append({"Metric": "NO POD", "Waarde": dq_dict["no_pod"]["count"]})
            dq_rows.append({"Metric": "Duplicaten", "Waarde": dq_dict["duplicaten"]["duplicaten"]})
            for kolom, info in dq_dict["missing"].items():
                if info["count"] > 0:
                    dq_rows.append({"Metric": f"Missing: {kolom}", "Waarde": info["count"]})
            pd.DataFrame(dq_rows).to_excel(writer, index=False, sheet_name="Data Quality")
        return output.getvalue()

    excel_data = _maak_recon_excel(recon, kv, dq)
    st.download_button(
        "📥 Download reconciliatie (Excel)",
        data=excel_data,
        file_name="otd_reconciliatie.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
