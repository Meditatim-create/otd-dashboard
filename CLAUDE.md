# OTD Dashboard — Elho B.V.

## Project
On-Time Delivery dashboard met 6 logistics performances, root-cause analyse en chat assistent.
Streamlit + Pandas + Plotly + Supabase + OpenAI.

## Datamodel
Twee data-inputs:
1. **Datagrid** (PowerBI export) — orderdata, performances, klantinfo
2. **LIKP** (SAP SE16n) — leveringen met Leveringstermijn en Pickdatum

Join key: `DeliveryNumber` (datagrid) = `Levering` (LIKP)

### 6 Logistics Performances
| # | Performance | Berekening | Status |
|---|------------|------------|--------|
| 1 | Planned Performance | Leveringstermijn > SAP Delivery Date → Late | Actief |
| 2 | Capacity Performance | "moved"/"not moved" uit PowerBI | Actief |
| 3 | Warehouse Performance | "On schedule" uit PowerBI | Actief |
| 4 | Carrier Pick-up | Geen data | Under construction |
| 5 | Carrier Departure | Geen data | Under construction |
| 6 | Carrier Transit | POD > Leveringstermijn → Late | Actief |

**OTD** = PODDeliveryDateShipment ≤ RequestedDeliveryDateFinal

## Conventies
- Nederlandse variabelen, labels en comments
- Elho branding: primair #76a73a, donker #0a4a2f
- Kolomnamen NIET lowercase maken — PowerBI/SAP gebruiken CamelCase
- String-vergelijkingen altijd lowercase + strip
- Imports: standaard lib → externe packages → lokale modules

## Commands
- `streamlit run app.py` — Start het dashboard
- `pip install -r requirements.txt` — Installeer dependencies

## Structuur
- `app.py` — Entry point, twee uploads (Datagrid + LIKP), routing
- `src/data/` — Loader, validator, processor (join + performances), database
- `src/pages/` — Dashboard pagina's + assistent
- `src/components/` — KPI kaarten, charts, waterfall, chat, filters
- `src/utils/` — Constants (6 performances), date helpers, LLM service

## Secrets
- `.streamlit/secrets.toml` — Supabase + LLM credentials (NIET in git)
- `.streamlit/secrets.toml.example` — Template met instructies
