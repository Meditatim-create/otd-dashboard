"""Constanten voor het OTD Dashboard."""

# Elho branding
ELHO_GROEN = "#76a73a"
ELHO_DONKER = "#0a4a2f"
ELHO_LICHT = "#f0f5e8"
ROOD = "#e74c3c"
GRIJS = "#95a5a6"

# KPI definities — volgorde = ketenverloop
KPI_STAPPEN = [
    {"id": "vrijgave_ok", "naam": "Vrijgave", "afdeling": "Customer Care", "nummer": 1},
    {"id": "tms_ok", "naam": "TMS Verwerking", "afdeling": "Logistiek", "nummer": 2},
    {"id": "bucket_ok", "naam": "Bucket Planning", "afdeling": "Logistiek", "nummer": 3},
    {"id": "warehouse_ok", "naam": "Warehouse", "afdeling": "Logistiek", "nummer": 4},
    {"id": "ophaling_ok", "naam": "Ophaling", "afdeling": "Logistiek", "nummer": 5},
    {"id": "vertrek_ok", "naam": "Vertrek", "afdeling": "Logistiek", "nummer": 6},
    {"id": "pod_ok", "naam": "POD", "afdeling": "Logistiek", "nummer": 7},
]

KPI_IDS = [s["id"] for s in KPI_STAPPEN]
KPI_NAMEN = {s["id"]: s["naam"] for s in KPI_STAPPEN}

# Standaard targets (%)
DEFAULT_TARGETS = {
    "vrijgave_ok": 95.0,
    "tms_ok": 98.0,
    "bucket_ok": 96.0,
    "warehouse_ok": 95.0,
    "ophaling_ok": 94.0,
    "vertrek_ok": 95.0,
    "pod_ok": 92.0,
}

# Verwachte kolommen in CSV
VERPLICHTE_KOLOMMEN = [
    "ordernummer",
    "klant",
    "gewenste_leverdatum",
    "werkelijke_leverdatum",
] + KPI_IDS

OPTIONELE_KOLOMMEN = [
    "productgroep",
    "regio",
    "beloofde_leverdatum",
]

DATUM_KOLOMMEN = [
    "gewenste_leverdatum",
    "beloofde_leverdatum",
    "werkelijke_leverdatum",
]

# Kleuren voor waterval
WATERVAL_KLEUREN = {
    "ok": ELHO_GROEN,
    "faal": ROOD,
    "totaal": ELHO_DONKER,
}
