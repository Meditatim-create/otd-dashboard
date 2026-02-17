"""Supabase database connectie en queries."""

import pandas as pd
import streamlit as st


def _get_client():
    """Maak Supabase client aan met secrets."""
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def heeft_database_config() -> bool:
    """Controleer of Supabase secrets geconfigureerd zijn."""
    try:
        return "supabase" in st.secrets and st.secrets["supabase"].get("url")
    except Exception:
        return False


def laad_orders() -> pd.DataFrame | None:
    """Laad alle orders uit de Supabase tabel."""
    try:
        client = _get_client()
        response = client.table("orders").select("*").execute()
        if not response.data:
            return None
        df = pd.DataFrame(response.data)
        # Verwijder Supabase metadata kolommen
        for kolom in ["id", "created_at"]:
            if kolom in df.columns:
                df = df.drop(columns=[kolom])
        return df
    except Exception as e:
        st.error(f"Fout bij laden uit database: {e}")
        return None


def upload_orders(df: pd.DataFrame) -> bool:
    """Upload DataFrame naar Supabase orders tabel (vervangt bestaande data)."""
    try:
        client = _get_client()
        # Bestaande data verwijderen
        client.table("orders").delete().neq("ordernummer", "").execute()
        # Nieuwe data uploaden in batches van 500
        records = df.to_dict(orient="records")
        batch_grootte = 500
        for i in range(0, len(records), batch_grootte):
            batch = records[i:i + batch_grootte]
            client.table("orders").insert(batch).execute()
        return True
    except Exception as e:
        st.error(f"Fout bij uploaden naar database: {e}")
        return False


def aantal_orders() -> int:
    """Tel het aantal orders in de database."""
    try:
        client = _get_client()
        response = client.table("orders").select("ordernummer", count="exact").execute()
        return response.count or 0
    except Exception:
        return 0


# SQL voor het aanmaken van de orders tabel (voor in Supabase SQL editor)
TABEL_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ordernummer TEXT NOT NULL,
    klant TEXT NOT NULL,
    gewenste_leverdatum DATE NOT NULL,
    werkelijke_leverdatum DATE,
    beloofde_leverdatum DATE,
    vrijgave_ok BOOLEAN DEFAULT FALSE,
    tms_ok BOOLEAN DEFAULT FALSE,
    bucket_ok BOOLEAN DEFAULT FALSE,
    warehouse_ok BOOLEAN DEFAULT FALSE,
    ophaling_ok BOOLEAN DEFAULT FALSE,
    vertrek_ok BOOLEAN DEFAULT FALSE,
    pod_ok BOOLEAN DEFAULT FALSE,
    productgroep TEXT,
    regio TEXT
);

-- Row Level Security inschakelen
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: alleen authenticated users mogen lezen
CREATE POLICY "Authenticated users can read orders"
    ON orders FOR SELECT
    TO authenticated
    USING (true);

-- Policy: alleen service_role mag schrijven (via API key)
CREATE POLICY "Service role can insert orders"
    ON orders FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "Service role can delete orders"
    ON orders FOR DELETE
    TO service_role
    USING (true);
"""
