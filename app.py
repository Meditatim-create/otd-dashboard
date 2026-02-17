"""OTD Dashboard — On-Time Delivery Rapportage voor Elho B.V."""

import streamlit as st

from src.data.loader import upload_bestand, laad_uit_database
from src.data.database import heeft_database_config, upload_orders, aantal_orders
from src.data.validator import valideer_en_verwerk
from src.components.filters import render_filters
from src.pages.overview import render_overview
from src.pages.customer_care import render_customer_care
from src.pages.logistics import render_logistics
from src.pages.root_cause import render_root_cause
from src.pages.trends import render_trends
from src.pages.assistent import render_assistent
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

# Sidebar: databron keuze
with st.sidebar:
    st.header("📁 Data")
    db_beschikbaar = heeft_database_config()

    if db_beschikbaar:
        databron = st.radio(
            "Databron",
            ["Database", "CSV Upload"],
            horizontal=True,
            help="Kies of je data uit de database of via CSV upload wilt laden.",
        )
    else:
        databron = "CSV Upload"

    if databron == "Database":
        n_orders = aantal_orders()
        if n_orders > 0:
            st.success(f"📊 {n_orders} orders in database")
            if st.button("🔄 Herlaad data"):
                st.session_state.df = None
            if st.session_state.df is None:
                df_raw = laad_uit_database()
                if df_raw is not None:
                    df_valid = valideer_en_verwerk(df_raw)
                    if df_valid is not None:
                        st.session_state.df = voeg_periode_kolommen_toe(df_valid)
        else:
            st.info("Database is leeg. Upload data via het admin-paneel hieronder.")

        # Admin: CSV naar database upload
        st.markdown("---")
        st.subheader("⬆️ Data naar database")
        admin_bestand = upload_bestand()
        if admin_bestand is not None:
            df_admin = valideer_en_verwerk(admin_bestand)
            if df_admin is not None:
                st.warning(f"Dit vervangt alle {n_orders} bestaande orders met {len(df_admin)} nieuwe orders.")
                if st.button("✅ Upload naar database"):
                    with st.spinner("Uploaden..."):
                        if upload_orders(df_admin):
                            st.success(f"✅ {len(df_admin)} orders opgeslagen in database!")
                            st.session_state.df = voeg_periode_kolommen_toe(df_admin)
                            st.rerun()
    else:
        df_raw = upload_bestand()
        if df_raw is not None:
            df_valid = valideer_en_verwerk(df_raw)
            if df_valid is not None:
                st.session_state.df = voeg_periode_kolommen_toe(df_valid)

if st.session_state.df is None:
    st.info("👆 Upload een CSV of Excel bestand via de sidebar om te beginnen.")
    st.markdown("---")
    st.markdown("""
    ### Verwacht formaat
    Het bestand moet minimaal de volgende kolommen bevatten:

    | Kolom | Beschrijving |
    |---|---|
    | `ordernummer` | Uniek ordernummer |
    | `klant` | Klantnaam |
    | `gewenste_leverdatum` | Door klant gewenste datum |
    | `werkelijke_leverdatum` | Daadwerkelijke levering |
    | `vrijgave_ok` | Customer Care: op tijd vrijgegeven? (0/1) |
    | `tms_ok` | TMS correct verwerkt? (0/1) |
    | `bucket_ok` | Juiste bucket planning? (0/1) |
    | `warehouse_ok` | Correct verwerkt in warehouse? (0/1) |
    | `ophaling_ok` | Vervoerder op tijd opgehaald? (0/1) |
    | `vertrek_ok` | Op tijd vertrokken? (0/1) |
    | `pod_ok` | Proof of Delivery op tijd? (0/1) |

    **Optioneel:** `productgroep`, `regio`, `beloofde_leverdatum`
    """)
    st.stop()

# Filters toepassen
df_filtered = render_filters(st.session_state.df)

if len(df_filtered) == 0:
    st.warning("Geen orders gevonden voor de geselecteerde filters.")
    st.stop()

# Pagina navigatie
pagina = st.radio(
    "Navigatie",
    ["Overzicht", "Customer Care", "Logistiek", "Root-Cause", "Trends", "Assistent"],
    horizontal=True,
    label_visibility="collapsed",
)

st.markdown("---")

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
