"""Constanten voor het OTD Dashboard — 6 Logistics Performances."""

# Elho branding
ELHO_GROEN = "#76a73a"
ELHO_DONKER = "#0a4a2f"
ELHO_LICHT = "#f0f5e8"
ROOD = "#e74c3c"
GRIJS = "#95a5a6"
ORANJE = "#e67e22"

# 6 Logistics Performances — volgorde = ketenverloop
PERFORMANCE_STAPPEN = [
    {
        "id": "planned_performance_ok",
        "naam": "Planned Performance",
        "nummer": 1,
        "beschikbaar": True,
        "beschrijving": "TMS-datum vs SAP Delivery Date",
    },
    {
        "id": "capacity_performance_ok",
        "naam": "Capacity Performance",
        "nummer": 2,
        "beschikbaar": True,
        "beschrijving": "Bucket planning (moved/not moved)",
    },
    {
        "id": "warehouse_performance_ok",
        "naam": "Warehouse Performance",
        "nummer": 3,
        "beschikbaar": True,
        "beschrijving": "Actual GI vs Planned GI",
    },
    {
        "id": "carrier_pickup_ok",
        "naam": "Carrier Pick-up",
        "nummer": 4,
        "beschikbaar": False,
        "beschrijving": "Under construction — geen data beschikbaar",
    },
    {
        "id": "carrier_departure_ok",
        "naam": "Carrier Departure",
        "nummer": 5,
        "beschikbaar": False,
        "beschrijving": "Under construction — geen data beschikbaar",
    },
    {
        "id": "carrier_transit_ok",
        "naam": "Carrier Transit",
        "nummer": 6,
        "beschikbaar": True,
        "beschrijving": "POD vs TMS-datum",
    },
]

PERFORMANCE_IDS = [s["id"] for s in PERFORMANCE_STAPPEN]
PERFORMANCE_NAMEN = {s["id"]: s["naam"] for s in PERFORMANCE_STAPPEN}
BESCHIKBARE_STAPPEN = [s for s in PERFORMANCE_STAPPEN if s["beschikbaar"]]
BESCHIKBARE_IDS = [s["id"] for s in BESCHIKBARE_STAPPEN]

# Standaard targets (%)
DEFAULT_TARGETS = {
    "planned_performance_ok": 95.0,
    "capacity_performance_ok": 95.0,
    "warehouse_performance_ok": 95.0,
    "carrier_pickup_ok": 95.0,
    "carrier_departure_ok": 95.0,
    "carrier_transit_ok": 92.0,
}

# Datagrid kolommen (PowerBI export) — case-sensitive originele namen
DATAGRID_KOLOMMEN = [
    "ChainCode", "CustomerNumber", "ChainName", "Country", "SalesArea",
    "SalesOrderNumber", "DeliveryNumber", "Creation Date order",
    "RequestedDeliveryDateIdoc", "SAP Delivery Date", "DeliveryDateInitial",
    "PODDeliveryDateShipment", "Planned GI Date", "Delivery_PlannedGIDate",
    "Actual GI Date", "GoodsIssueTime", "GoodsIssueDateCarrier",
    "ShipmentNumber", "Carrier", "RequestedDeliveryDateFinal",
    "Creation WeekNumber", "Requested WeekNumber", "Planned GI WeekNumber",
    "DAYS_TO_LATE", "DAYS_DELAY_GI",
    "PERFORMANCE_CAPACITY", "PERFORMANCE_TRANSPORT", "PERFORMANCE_LOGISTIC",
    "PERFORMANCE_CUSTOMER", "NewBookingSlot", "ReasonCodeLatesCorrected",
    "CommentLateOrders", "PERFORMANCE_CUSTOMER_FINAL", "BookIn", "BookinBy",
    "BookInVia", "Fixed", "PERFORMANCE_CUSTOMER_BOOK_IN",
]

# Verplichte kolommen in Datagrid
VERPLICHTE_DATAGRID_KOLOMMEN = [
    "DeliveryNumber", "SAP Delivery Date", "RequestedDeliveryDateFinal",
    "PODDeliveryDateShipment", "PERFORMANCE_CAPACITY", "PERFORMANCE_LOGISTIC",
]

# LIKP kolommen (SAP SE16n)
LIKP_KOLOMMEN = {
    "levering": "Levering",
    "leveringstermijn": "Leveringstermijn",
    "pickdatum": "Pickdatum",
    "gecreeerd_op": "Gecreëerd op",
}

VERPLICHTE_LIKP_KOLOMMEN = ["Levering", "Leveringstermijn", "Pickdatum"]

# Datumkolommen per bron
DATAGRID_DATUM_KOLOMMEN = [
    "Creation Date order", "RequestedDeliveryDateIdoc", "SAP Delivery Date",
    "DeliveryDateInitial", "PODDeliveryDateShipment", "Planned GI Date",
    "Delivery_PlannedGIDate", "Actual GI Date", "GoodsIssueDateCarrier",
    "RequestedDeliveryDateFinal", "BookIn",
]

LIKP_DATUM_KOLOMMEN = ["Leveringstermijn", "Pickdatum", "Gecreëerd op"]

# Kleuren voor waterval
WATERVAL_KLEUREN = {
    "ok": ELHO_GROEN,
    "faal": ROOD,
    "totaal": ELHO_DONKER,
}

# Action Portal configuratie
ACTION_PORTAL_PAD = r"C:\Users\tim.denheijer\OneDrive - elho\Documents\07_Projecten\action-portal-scraper\downloads"

ACTION_PORTAL_DATUM_KOLOMMEN = [
    "Appointment", "Arrival", "Start unloading", "Finished unloading", "Cancel date",
]

# Time labels: welke tellen als "op tijd"
ACTION_TIME_LABEL_GOED = ["Early", "On time"]
ACTION_TIME_LABEL_SLECHT = ["Late", "Late - Reported"]
