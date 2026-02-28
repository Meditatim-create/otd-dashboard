"""Feedback manager — slaat correcties op als YAML in feedback/ map."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml


_PROJECT_DIR = Path(__file__).resolve().parent.parent
_FEEDBACK_DIR = _PROJECT_DIR / "feedback"


def bewaar_feedback(vraag: str, antwoord: str, correctie: str) -> Path:
    """Sla een correctie op als YAML-bestand in feedback/.

    Retourneert het pad naar het opgeslagen bestand.
    """
    _FEEDBACK_DIR.mkdir(exist_ok=True)

    nu = datetime.now()
    bestandsnaam = nu.strftime("%Y-%m-%d_%H%M%S") + ".yaml"
    pad = _FEEDBACK_DIR / bestandsnaam

    data = {
        "datum": nu.isoformat(),
        "vraag": vraag,
        "antwoord": antwoord,
        "correctie": correctie,
    }

    with open(pad, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    return pad


def laad_feedback(limit: int = 10) -> list[dict]:
    """Laad de laatste N feedback-bestanden, nieuwste eerst."""
    if not _FEEDBACK_DIR.exists():
        return []

    bestanden = sorted(_FEEDBACK_DIR.glob("*.yaml"), reverse=True)

    resultaten = []
    for bestand in bestanden[:limit]:
        try:
            with open(bestand, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data:
                    resultaten.append(data)
        except Exception:
            continue

    return resultaten


def feedback_als_tekst(limit: int = 10) -> str:
    """Geef feedback terug als leesbare tekst voor LLM-context."""
    items = laad_feedback(limit)
    if not items:
        return ""

    regels = ["Eerdere correcties van de gebruiker:"]
    for item in items:
        datum = item.get("datum", "?")[:10]
        vraag = item.get("vraag", "?")
        correctie = item.get("correctie", "?")
        regels.append(f"  [{datum}] Vraag: {vraag}")
        regels.append(f"           Correctie: {correctie}")

    return "\n".join(regels)
