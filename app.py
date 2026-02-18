"""OTD Dashboard — On-Time Delivery Rapportage voor Elho B.V."""

import streamlit as st

from src.data.loader import upload_datagrid, upload_likp, laad_action_portal
from src.data.validator import valideer_datagrid, valideer_likp
from src.data.processor import join_likp, bereken_performances
from src.components.filters import render_filters
from src.pages.overview import render_overview
from src.pages.customer_care import render_customer_care
from src.pages.logistics import render_logistics
from src.pages.root_cause import render_root_cause
from src.pages.trends import render_trends
from src.pages.assistent import render_assistent
from src.pages.action_portal import render_action_portal
from src.utils.date_utils import voeg_periode_kolommen_toe

st.set_page_config(
    page_title="OTD Dashboard — Elho",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Header
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
        <h1 style="margin: 0; color: #0a4a2f;">📦 OTD Dashboard</h1>
        <span style="color: #76a73a; font-size: 1.1rem;">Elho B.V.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Data initialisatie
if "df" not in st.session_state:
    st.session_state.df = None

# Action Portal data auto-laden
if "df_action" not in st.session_state:
    st.session_state.df_action = laad_action_portal()

# Sidebar: twee uploads
with st.sidebar:
    st.header("📁 Data Upload")
    st.caption("Upload beide bestanden om het dashboard te laden.")

    df_datagrid_raw = upload_datagrid()
    df_likp_raw = upload_likp()

    if df_datagrid_raw is not None and df_likp_raw is not None:
        df_dg = valideer_datagrid(df_datagrid_raw)
        df_lk = valideer_likp(df_likp_raw)

        if df_dg is not None and df_lk is not None:
            # Join en performances berekenen
            df_joined = join_likp(df_dg, df_lk)
            df_processed = bereken_performances(df_joined)
            st.session_state.df = voeg_periode_kolommen_toe(df_processed)
            st.success(f"📊 {len(df_processed)} orders verwerkt met {len(df_lk)} LIKP-leveringen")

    elif df_datagrid_raw is not None:
        st.info("⏳ Upload ook het LIKP bestand om te beginnen.")
    elif df_likp_raw is not None:
        st.info("⏳ Upload ook het Datagrid bestand om te beginnen.")

# Pagina navigatie — Action Portal altijd beschikbaar
pagina_opties = ["Overzicht", "Customer Care", "Logistiek", "Root-Cause", "Trends", "Assistent", "Action Portal"]
pagina = st.radio(
    "Navigatie",
    pagina_opties,
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("---")

# Action Portal heeft eigen data en filters — geen upload nodig
if pagina == "Action Portal":
    if st.session_state.df_action is not None:
        render_action_portal(st.session_state.df_action)
    else:
        st.warning("Geen Action Portal data gevonden. Controleer of er AppointmentReport bestanden staan in de action-portal-scraper downloads map.")
    st.stop()

# Overige pagina's: Datagrid + LIKP data vereist
if st.session_state.df is None:
    st.info("Upload de Datagrid (PowerBI) en LIKP (SAP) bestanden via de sidebar om te beginnen.")
    st.markdown("---")
    st.markdown("""
    ### Verwacht formaat

    **Datagrid** (PowerBI export):
    | Kolom | Beschrijving |
    |---|---|
    | `DeliveryNumber` | Leveringsnummer (join key met LIKP) |
    | `SAP Delivery Date` | Geplande leverdatum in SAP |
    | `RequestedDeliveryDateFinal` | Door klant gewenste leverdatum |
    | `PODDeliveryDateShipment` | Proof of Delivery datum |
    | `PERFORMANCE_CAPACITY` | "moved" / "not moved" |
    | `PERFORMANCE_LOGISTIC` | "On schedule" / etc. |

    **Optioneel:** ChainName, Country, SalesArea, Carrier, ReasonCodeLatesCorrected, CommentLateOrders

    ---

    **LIKP** (SAP SE16n):
    | Kolom | Beschrijving |
    |---|---|
    | `Levering` | Leveringsnummer (join key) |
    | `Leveringstermijn` | Geplande leverdatum TMS |
    | `Pickdatum` | Geplande pickdatum |

    **Optioneel:** Gecreëerd op
    """)
    st.stop()

# Filters toepassen
df_filtered = render_filters(st.session_state.df)

if len(df_filtered) == 0:
    st.warning("Geen orders gevonden voor de geselecteerde filters.")
    st.stop()

if pagina == "Overzicht":
    render_overview(df_filtered)
elif pagina == "Customer Care":
    render_customer_care(df_filtered)
elif pagina == "Logistiek":
    render_logistics(df_filtered)
elif pagina == "Root-Cause":
    render_root_cause(df_filtered)
elif pagina == "Trends":
    render_trends(df_filtered)
elif pagina == "Assistent":
    render_assistent(df_filtered)
