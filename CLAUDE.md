# OTD Dashboard — Elho B.V.

## Project
On-Time Delivery dashboard met root-cause analyse en chat assistent. Streamlit + Pandas + Plotly + Supabase + OpenAI.

## Conventies
- Nederlandse variabelen, labels en comments
- Elho branding: primair #76a73a, donker #0a4a2f
- KPI-stappen altijd in ketenvolgorde (1-7)
- Imports: standaard lib → externe packages → lokale modules

## Commands
- `streamlit run app.py` — Start het dashboard
- `pip install -r requirements.txt` — Installeer dependencies

## Structuur
- `app.py` — Entry point, routing, databron keuze
- `src/data/` — Loader, validator, processor, database (Supabase)
- `src/pages/` — Dashboard pagina's + assistent
- `src/components/` — Herbruikbare UI componenten + chat
- `src/utils/` — Constants, date helpers, LLM service

## Secrets
- `.streamlit/secrets.toml` — Supabase + LLM credentials (NIET in git)
- `.streamlit/secrets.toml.example` — Template met instructies
