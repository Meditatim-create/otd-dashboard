# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- `streamlit run app.py` — Start het dashboard (localhost:8501)
- `pip install -r requirements.txt` — Installeer dependencies (streamlit, pandas, plotly, openpyxl, supabase, openai)

## Architecture

Streamlit dashboard voor On-Time Delivery analyse bij Elho B.V. Data flow:

```
Upload (Datagrid + LIKP) → Validate → Join → Calculate 6 performances → Filter → Render pages
```

**Entry point** `app.py`: twee file uploaders in sidebar, caching via session_state, routing naar 7 pagina's, Excel export.

### Data Model — Twee inputs + join
- **Datagrid** (PowerBI export, 38+ kolommen): orderdata, klantinfo, PowerBI performance flags. Key: `DeliveryNumber`
- **LIKP** (SAP SE16n, 207 kolommen): leveringen. Relevante kolommen: `Levering` (join key), `Leveringstermijn`, `Pickdatum`
- Left join in `processor.py::join_likp()` op `DeliveryNumber = Levering` (string match). Retourneert ook mismatches.

### 6 Logistics Performances (berekend in `processor.py::bereken_performances()`)
| # | Performance | Berekening | Status |
|---|------------|------------|--------|
| 1 | Planned Performance | `Leveringstermijn ≤ SAP Delivery Date` | Actief |
| 2 | Capacity Performance | `PERFORMANCE_CAPACITY ≠ "not moved"` | Actief |
| 3 | Warehouse Performance | `PERFORMANCE_LOGISTIC = "On schedule"` | Actief |
| 4 | Carrier Pick-up | Geen data | Under construction |
| 5 | Carrier Departure | Geen data | Under construction |
| 6 | Carrier Transit | `PODDeliveryDateShipment ≤ Leveringstermijn` | Actief |

**OTD** = `PODDeliveryDateShipment ≤ RequestedDeliveryDateFinal`

Performances zijn nullable booleans (True/False/NaN). NaN = geen data, wordt uitgesloten bij berekeningen. Under construction stappen (#4, #5): `beschikbaar: False` in constants, UI toont ze grijs. Activeren = `beschikbaar: True` zetten + berekening toevoegen.

### Root Cause Logic
`bereken_root_causes()`: voor elke te late order, loop door de 4 beschikbare stappen in volgorde. Eerste `False` = root cause. NaN = skip. Alle True = "onbekend".

### Action Portal (apart feature)
Laadt automatisch nieuwste `AppointmentReport_*.xlsx` uit action-portal-scraper downloads. Eigen data, eigen filters, geen join met Datagrid/LIKP nodig.

## Key Modules
| File | Verantwoordelijkheid |
|------|---------------------|
| `src/utils/constants.py` | Alle constanten: 6 performance-definities, kleuren, kolomnamen, targets. Geïmporteerd door bijna elk module. |
| `src/data/processor.py` | Alle berekeningen: join, 6 performances, OTD, root causes, waterval, trends |
| `src/components/filters.py` | Sidebar filters (periode, ChainName, Country, SalesArea, Carrier) + target inputs |
| `src/utils/llm_service.py` | Optionele chat: OpenRouter of Azure OpenAI. Graceful fallback als secrets ontbreken. |

## Conventions
- **Taal**: Nederlandse variabelen, labels, comments (`bereken_otd`, `voeg_periode_kolommen_toe`)
- **Kolomnamen NIET lowercase maken** — PowerBI/SAP gebruiken CamelCase (`DeliveryNumber`, `SAP Delivery Date`). Berekende kolommen zijn snake_case (`planned_performance_ok`)
- **String-vergelijkingen**: altijd `.str.strip().str.lower()` voor vergelijking
- **Datums**: `dayfirst=True` (Europees formaat), `errors="coerce"`
- **Branding**: primair `#76a73a` (groen), donker `#0a4a2f`, rood `#e74c3c`, grijs `#95a5a6`
- **Formatting**: percentages `{:.1f}%`, counts `{:.0f}`, NaN weergeven als "—"
- **Imports**: standaard lib → externe packages → lokale modules (`src.*`)

## Secrets
- `.streamlit/secrets.toml` (gitignored): LLM config (`provider`, `api_key`, `model`) + optioneel Supabase (`url`, `key`)
- `.streamlit/secrets.toml.example` — Template
