"""Configuratie module — laadt rekenmodel.yaml en biedt helpers."""

from __future__ import annotations

from pathlib import Path

import yaml


# Pad naar rekenmodel.yaml (naast app.py)
_PROJECT_DIR = Path(__file__).resolve().parent.parent
_REKENMODEL_PAD = _PROJECT_DIR / "rekenmodel.yaml"

# Defaults als bestand ontbreekt (recalculate = originele logica)
_DEFAULTS = {
    "no_pod": {"exclude_from_denominator": True},
    "otd": {
        "method": "recalculate",
    },
    "performances": {
        "planned_performance_ok": {
            "naam": "Planned Performance",
            "nummer": 1,
            "beschikbaar": True,
            "method": "recalculate",
            "dates": ["Leveringstermijn", "SAP Delivery Date"],
        },
        "capacity_performance_ok": {
            "naam": "Capacity Performance",
            "nummer": 2,
            "beschikbaar": True,
            "method": "column",
            "source_column": "PERFORMANCE_CAPACITY",
            "ok_values": ["not moved"],
        },
        "warehouse_performance_ok": {
            "naam": "Warehouse Performance",
            "nummer": 3,
            "beschikbaar": True,
            "method": "column",
            "source_column": "PERFORMANCE_LOGISTIC",
            "ok_values": ["On schedule"],
        },
        "carrier_pickup_ok": {
            "naam": "Carrier Pick-up",
            "nummer": 4,
            "beschikbaar": False,
        },
        "carrier_departure_ok": {
            "naam": "Carrier Departure",
            "nummer": 5,
            "beschikbaar": False,
        },
        "carrier_transit_ok": {
            "naam": "Carrier Transit",
            "nummer": 6,
            "beschikbaar": True,
            "method": "recalculate",
            "dates": ["PODDeliveryDateShipment", "Leveringstermijn"],
        },
    },
}

_config_cache: dict | None = None


def laad_config() -> dict:
    """Laad rekenmodel.yaml. Val terug op defaults als bestand ontbreekt."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if _REKENMODEL_PAD.exists():
        with open(_REKENMODEL_PAD, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = _DEFAULTS.copy()

    return _config_cache


def herlaad_config() -> dict:
    """Forceer herladen van config (na wijzigingen)."""
    global _config_cache
    _config_cache = None
    return laad_config()


def get_dedup_config() -> dict:
    """Haal dedup-configuratie op."""
    cfg = laad_config()
    return cfg.get("dedup", {"enabled": False})


def get_otd_config() -> dict:
    """Haal OTD-configuratie op."""
    cfg = laad_config()
    return cfg.get("otd", _DEFAULTS["otd"])


def get_no_pod_config() -> dict:
    """Haal no-POD configuratie op."""
    cfg = laad_config()
    return cfg.get("no_pod", _DEFAULTS["no_pod"])


def get_performance_config(kpi_id: str) -> dict:
    """Haal configuratie op voor één performance-stap."""
    cfg = laad_config()
    performances = cfg.get("performances", {})
    return performances.get(kpi_id, {})


def get_alle_performances() -> dict[str, dict]:
    """Haal alle performance-configuraties op."""
    cfg = laad_config()
    return cfg.get("performances", _DEFAULTS["performances"])


def bouw_performance_stappen() -> list[dict]:
    """Bouw PERFORMANCE_STAPPEN lijst op vanuit config (compatibel met constants.py)."""
    performances = get_alle_performances()
    stappen = []
    for kpi_id, perf_cfg in performances.items():
        stappen.append({
            "id": kpi_id,
            "naam": perf_cfg.get("naam", kpi_id),
            "nummer": perf_cfg.get("nummer", 0),
            "beschikbaar": perf_cfg.get("beschikbaar", False),
            "beschrijving": perf_cfg.get("beschrijving", ""),
        })
    stappen.sort(key=lambda s: s["nummer"])
    return stappen


def toon_config_tekst() -> str:
    """Leesbare samenvatting van het huidige rekenmodel."""
    cfg = laad_config()
    regels = ["=== Huidig Rekenmodel ===", ""]

    # OTD
    otd = cfg.get("otd", {})
    method = otd.get("method", "recalculate")
    regels.append(f"OTD ({method}):")
    if method == "column":
        regels.append(f"  Bron: kolom '{otd.get('source_column', '?')}'")
        regels.append(f"  OK-waarden: {otd.get('ok_values', [])}")
        if otd.get("no_pod_values"):
            regels.append(f"  No-POD waarden: {otd['no_pod_values']}")
    else:
        regels.append("  Herberekend: POD <= RequestedDeliveryDateFinal")

    # No POD
    no_pod = cfg.get("no_pod", {})
    if no_pod.get("exclude_from_denominator"):
        regels.append("")
        regels.append("No-POD: uitgesloten van noemer (ELHO standaard)")

    # Performances
    regels.append("")
    regels.append("Performances:")
    performances = cfg.get("performances", {})
    for kpi_id, perf_cfg in performances.items():
        naam = perf_cfg.get("naam", kpi_id)
        nummer = perf_cfg.get("nummer", "?")
        beschikbaar = perf_cfg.get("beschikbaar", False)

        if not beschikbaar:
            regels.append(f"  {nummer}. {naam}: NIET BESCHIKBAAR")
            continue

        method = perf_cfg.get("method", "?")
        if method == "column":
            src = perf_cfg.get("source_column", "?")
            ok = perf_cfg.get("ok_values", [])
            regels.append(f"  {nummer}. {naam}: kolom '{src}' -> OK als {ok}")
        elif method == "recalculate":
            dates = perf_cfg.get("dates", [])
            regels.append(f"  {nummer}. {naam}: herbereken uit {dates}")
        else:
            regels.append(f"  {nummer}. {naam}: methode '{method}'")

    return "\n".join(regels)
