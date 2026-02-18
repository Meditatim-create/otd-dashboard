"""Supabase database connectie en queries."""

from __future__ import annotations

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
        response = client.table("otd_orders").select("*").execute()
        if not response.data:
            return None
        df = pd.DataFrame(response.data)
        for kolom in ["id", "created_at"]:
            if kolom in df.columns:
                df = df.drop(columns=[kolom])
        return df
    except Exception as e:
        st.error(f"Fout bij laden uit database: {e}")
        return None


def upload_orders(df: pd.DataFrame) -> bool:
    """Upload DataFrame naar Supabase otd_orders tabel (vervangt bestaande data)."""
    try:
        client = _get_client()
        client.table("otd_orders").delete().neq("DeliveryNumber", "").execute()
        records = df.to_dict(orient="records")
        batch_grootte = 500
        for i in range(0, len(records), batch_grootte):
            batch = records[i:i + batch_grootte]
            client.table("otd_orders").insert(batch).execute()
        return True
    except Exception as e:
        st.error(f"Fout bij uploaden naar database: {e}")
        return False


def aantal_orders() -> int:
    """Tel het aantal orders in de database."""
    try:
        client = _get_client()
        response = client.table("otd_orders").select("DeliveryNumber", count="exact").execute()
        return response.count or 0
    except Exception:
        return 0


# SQL voor het aanmaken van de otd_orders tabel (voor in Supabase SQL editor)
TABEL_SQL = """
CREATE TABLE IF NOT EXISTS otd_orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Identifiers
    "ChainCode" TEXT,
    "CustomerNumber" TEXT,
    "ChainName" TEXT,
    "Country" TEXT,
    "SalesArea" TEXT,
    "SalesOrderNumber" TEXT,
    "DeliveryNumber" TEXT NOT NULL,
    "ShipmentNumber" TEXT,
    "Carrier" TEXT,

    -- Datums
    "Creation Date order" DATE,
    "RequestedDeliveryDateIdoc" DATE,
    "SAP Delivery Date" DATE,
    "DeliveryDateInitial" DATE,
    "PODDeliveryDateShipment" DATE,
    "Planned GI Date" DATE,
    "Delivery_PlannedGIDate" DATE,
    "Actual GI Date" DATE,
    "GoodsIssueDateCarrier" DATE,
    "RequestedDeliveryDateFinal" DATE,
    "BookIn" DATE,

    -- Weeknummers
    "Creation WeekNumber" TEXT,
    "Requested WeekNumber" TEXT,
    "Planned GI WeekNumber" TEXT,

    -- Metrics
    "DAYS_TO_LATE" NUMERIC,
    "DAYS_DELAY_GI" NUMERIC,
    "GoodsIssueTime" TEXT,

    -- Performances (string uit PowerBI)
    "PERFORMANCE_CAPACITY" TEXT,
    "PERFORMANCE_TRANSPORT" TEXT,
    "PERFORMANCE_LOGISTIC" TEXT,
    "PERFORMANCE_CUSTOMER" TEXT,
    "PERFORMANCE_CUSTOMER_FINAL" TEXT,
    "PERFORMANCE_CUSTOMER_BOOK_IN" TEXT,

    -- Extra velden
    "NewBookingSlot" TEXT,
    "ReasonCodeLatesCorrected" TEXT,
    "CommentLateOrders" TEXT,
    "BookinBy" TEXT,
    "BookInVia" TEXT,
    "Fixed" TEXT,

    -- LIKP data (na join)
    "Leveringstermijn" DATE,
    "Pickdatum" DATE,

    -- Berekende performance booleans
    planned_performance_ok BOOLEAN,
    capacity_performance_ok BOOLEAN,
    warehouse_performance_ok BOOLEAN,
    carrier_pickup_ok BOOLEAN,
    carrier_departure_ok BOOLEAN,
    carrier_transit_ok BOOLEAN
);

-- Row Level Security
ALTER TABLE otd_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read otd_orders"
    ON otd_orders FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Service role can insert otd_orders"
    ON otd_orders FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "Service role can delete otd_orders"
    ON otd_orders FOR DELETE
    TO service_role
    USING (true);
"""
