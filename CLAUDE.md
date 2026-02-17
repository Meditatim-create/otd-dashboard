# OTD Dashboard — Elho B.V.

## Project
On-Time Delivery dashboard met root-cause analyse. Streamlit + Pandas + Plotly.

## Conventies
- Nederlandse variabelen, labels en comments
- Elho branding: primair #76a73a, donker #0a4a2f
- KPI-stappen altijd in ketenvolgorde (1-7)
- Imports: standaard lib → externe packages → lokale modules

## Commands
- `streamlit run app.py` — Start het dashboard
- `pip install -r requirements.txt` — Installeer dependencies

## Structuur
- `app.py` — Entry point, routing
- `src/data/` — Loader, validator, processor
- `src/pages/` — Dashboard pagina's
- `src/components/` — Herbruikbare UI componenten
- `src/utils/` — Constants, date helpers
