# Flock ALPR Camera Placement vs. Neighbourhood Demographics

**Los Angeles County, CA · King County, WA**

Are Flock automated license plate readers placed disproportionately in
Hispanic/Latino neighbourhoods, after controlling for the innocent explanations
— road density, population, income and reported crime? And who can search the
data they collect?

3,025 mapped Flock cameras, 2,993 census tracts, 481,281 crime records and 42
policy documents, analysed end to end: collection → spatial joins → statistics
→ maps → document retrieval → a website.

**[Live site](https://flock-demographics-analysis.vercel.app)** ·
**[Full report with methodology and thesis](docs/report.md)** ·
[Plain-English findings](docs/findings.md) ·
[Data sources and limitations](docs/data_sources.md)

---

## What it found

| | Los Angeles County | King County |
| --- | --- | --- |
| Effect of +10pt Hispanic share on cameras per road-mile | −6.3% | **+30.3%** |
| p-value (within-city model) | 0.008 | 0.035 |
| Home improvement stores with a non-chain camera within 150 m | 46% vs 14% control | 43% vs 11% control |

Three results, in order of how much weight they carry:

1. **The counties disagree.** King County shows more cameras in more Hispanic
   tracts, surviving every control including within-city comparison. LA points
   slightly the other way. There is no single pattern across both.
2. **Home Depot and Lowe's carry ~5x the odds** of a nearby ALPR they do not
   own, compared with matched big-box retailers. Nearly identical in both
   counties — the most consistent finding here.
3. **Adoption is near-universal** (81 of 88 LA cities, 25 of 31 King), and
   adopting cities are demographically indistinguishable from the rest.

The camera data is crowdsourced and incomplete, and placement disparity is not
evidence of intent. Both caveats are load-bearing; see the report.

---

## The website

A static Next.js site: overview, full report, interactive maps, and an explorer
that queries the data and searches the documents.

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

**No API key, no account, no server.** DuckDB-WASM runs the 11,129-row analysis
table in the browser over an 0.8 MB Parquet file, and document search embeds
your question locally (Transformers.js) against 432 KB of quantised vectors.
Nothing is sent anywhere, so the deployed site costs nothing to run and has
nothing to abuse.

Deploy to Vercel with the repository root set to `web/`; it builds to fully
static output.

Regenerate everything the site serves:

```bash
.venv/bin/python src/analysis/export_web.py
```

---

## Requirements

- macOS or Linux, Python 3.13, Node 20+
- No database server: DuckDB and files only

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins direct dependencies; `requirements.lock.txt` is the
exact environment.

## The one key you need

A **Census API key**, free, for the demographic data. Everything else —
OpenStreetMap, crime portals, document downloads, embeddings — needs no
credentials.

1. Go to https://api.census.gov/data/key_signup.html
2. Enter an organisation name (a personal project name is fine) and your email.
3. Check your email; look in spam if it does not arrive within minutes.
4. **Click the activation link.** The key does not work until activated.
5. Copy `.env.example` to `.env` and paste the key after `CENSUS_API_KEY=`,
   no quotes or spaces.
6. Verify:

```bash
.venv/bin/python src/check_census_key.py
```

macOS hides dotfiles; press `Cmd+Shift+.` in Finder, or `open -e .env`.

`ANTHROPIC_API_KEY` is in `.env.example` but **is not required**. The site and
all analysis run without it. `rag/query.py --generate` uses it if present.

---

## Running the pipeline

```bash
# Phase 2 — collection (writes data/raw/)
python src/collect/census_acs.py            # ACS 2020-2024, tract + block group
python src/collect/tiger_boundaries.py      # tract/block-group polygons
python src/collect/tiger_places.py          # city boundaries
python src/collect/flock_cameras.py         # ALPR cameras via Overpass
python src/collect/osm_roads.py             # arterial roads
python src/collect/osm_retailers.py         # Home Depot / Lowe's
python src/collect/osm_control_retailers.py # Target, Walmart, Costco, ...
python src/collect/crime.py                 # LAPD + Seattle PD (NIBRS)
python src/collect/day_labor_sites.py       # candidate hiring sites
python src/collect/rag_documents.py         # 42 policy documents

# Phase 3 — clean and join
python src/analysis/build_units.py          # -> data/processed/*.gpkg + flock.duckdb

# Phase 4 — analysis (-> outputs/tables/)
python src/analysis/descriptive.py
python src/analysis/models.py
python src/analysis/city_adoption.py
python src/analysis/verify_day_labor.py
python src/analysis/retailer_test.py

# Phase 5 — maps and figures
python src/analysis/make_maps.py            # -> outputs/maps/ (Folium)
python src/analysis/make_figures.py         # -> outputs/figures/ (PNG)

# Phase 6 — document search
python rag/build_index.py --rebuild         # 1,125 chunks -> ChromaDB
python rag/query.py --samples               # cited answers, no API key
python rag/query.py "What does SB 34 prohibit?"

# Phase 7 — website payload
python src/analysis/export_web.py           # -> web/public/
```

OpenStreetMap and the crime portals change continuously, so re-running gives
different counts. Published figures are the 2026-09-23 camera snapshot.

---

## Method in brief

- **Unit of analysis:** census tract, with block groups as a robustness check.
- **Projection:** EPSG:2229 (LA) and EPSG:2285 (King) before any distance or
  length measurement.
- **Outcome:** Flock cameras excluding those operated by Home Depot and Lowe's,
  which are private placements rather than government ones.
- **Exposure:** arterial road-miles as a model offset, so the estimate is
  cameras *per road-mile*.
- **Model:** negative binomial (counts are overdispersed), with dispersion
  estimated via a Poisson auxiliary regression and HC1 robust standard errors.
- **Spatial:** Moran's I on residuals; queen contiguity; spatial lag model
  where residuals cluster (they do, in both counties).
- **Retailer test:** Fisher's exact against a matched big-box control group.

Full detail, including why each choice was made, is in
[docs/report.md](docs/report.md).

---

## Layout

```
data/raw/          source data, unchanged as downloaded
data/processed/    cleaned tables (GeoPackage + flock.duckdb)
src/collect/       one script per data source
src/analysis/      joins, models, figures, web export
outputs/tables/    result tables
outputs/figures/   report figures
outputs/maps/      Folium maps
rag/documents/     42 downloaded documents + sources.csv
rag/               chunking, embedding, query
web/               Next.js site
docs/              report, findings, data sources, manual downloads
```

## Honesty notes

- Camera locations are crowdsourced (DeFlock/OpenStreetMap). Coverage is
  incomplete and the gaps are probably not random. This limits every finding.
- Crime data covers the cities of LA and Seattle only — 44% and 36% of tracts.
  Missing is recorded as missing, never as zero.
- 86% of LA's mapped Flock cameras have no operator tag, so government and
  private cameras cannot be fully separated.
- The day-labor comparison is documentary, not field-verified, and returns no
  significant difference in LA and cannot run in King County.
- Three sources blocked automated download; they are listed in
  [docs/manual_downloads.md](docs/manual_downloads.md) rather than dropped.
