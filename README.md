# Flock ALPR Camera Placement vs. Demographics

Does the placement of Flock automated license plate reader (ALPR) cameras fall
disproportionately in Hispanic/Latino neighborhoods in **Los Angeles County, CA**
and **King County, WA (Seattle)** — after controlling for fair explanations such
as road density, population and reported crime?

The project adds two layers on top of that analysis: a document search tool (RAG)
over the policy and data-sharing record, and a plain-English query interface over
the results.

## What this project can and cannot show

Placement disparity is not proof of intent. Camera locations come largely from
crowdsourced data (DeFlock/OpenStreetMap) and are certainly incomplete; some
cameras are privately owned rather than placed by a government agency. Findings
are reported with these limits stated in `docs/findings.md`.

## Requirements

- macOS or Linux, Python 3.13
- No database server: analysis uses DuckDB (with its spatial extension) and files

## Setup

```bash
cd "/Users/junior/Projects/Flock Demographics Analysis"
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` holds the direct dependencies. `requirements.lock.txt` is the
full pinned environment if you need an exact rebuild.

## API keys

Keys live in `.env` and are never committed (`.gitignore` excludes it). Copy the
template and fill in the values:

```bash
cp .env.example .env
```

### Census API key (needed from Phase 2)

1. Go to https://api.census.gov/data/key_signup.html
2. Enter an organization name (a personal project name is fine) and your email,
   then submit.
3. Check your email for the key; look in spam if it does not arrive in a few
   minutes.
4. Click the activation link in the email. The key does not work until activated.
5. Paste the key into `.env` after `CENSUS_API_KEY=`, with no quotes or spaces.
6. Verify it:

```bash
.venv/bin/python src/check_census_key.py
```

### Anthropic API key (needed from Phase 7)

1. Sign in at https://console.anthropic.com
2. Add a payment method or buy credits. API usage is billed separately from a
   Claude subscription, and keys do not work without credits.
3. Optionally set a monthly spending limit.
4. Create a key in the API keys section and copy it immediately — the console
   shows it in full only once.
5. Paste it into `.env` after `ANTHROPIC_API_KEY=`, with no quotes or spaces.

macOS hides files beginning with a dot. Press `Cmd+Shift+.` in Finder to show
them, or open the file directly with `open -e .env`.

## Layout

```
data/raw/          source data, unchanged as downloaded
data/processed/    cleaned tables (GeoPackage + DuckDB)
src/collect/       one collection script per data source
src/analysis/      cleaning, spatial joins, models
notebooks/         exploratory work
outputs/maps/      interactive Folium maps
outputs/tables/    result tables
docs/              data sources, findings, manual download list
rag/documents/     downloaded policy documents + sources.csv
app/               Streamlit query interface
```

## Phases

| Phase | What it does | How to run |
| --- | --- | --- |
| 0 | Project folder | done |
| 1 | Setup, keys | `.venv/bin/python src/check_census_key.py` |
| 2 | Data collection | `src/collect/*.py` (see `docs/data_sources.md`) |
| 3 | Cleaning and spatial joins | `src/analysis/` |
| 4 | Analysis: descriptive, negative binomial, spatial, robustness | `src/analysis/` |
| 5 | Maps | `outputs/maps/` |
| 6 | Document search (RAG) | `rag/` |
| 7 | Plain-English query app | `streamlit run app/app.py` |

Each phase is run and reviewed before the next one starts. This table is updated
with exact commands as each phase lands.

## Data sources

Every dataset is recorded in `docs/data_sources.md` with its URL, download date,
row count and known limitations. Documents downloaded for the RAG layer are
listed in `rag/documents/sources.csv`. Anything paywalled or login-walled is
listed in `docs/manual_downloads.md` for manual retrieval.
