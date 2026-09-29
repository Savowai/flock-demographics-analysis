# Data sources

Every dataset used in this project, with where it came from, when it was
downloaded, how many rows it has, and what is wrong with it. Raw files are kept
unchanged in `data/raw/`.

Collection scripts live in `src/collect/`. Re-running a script re-downloads the
source, which for the OSM and crime sources will produce different counts,
because those datasets change continuously.

---

## 1. Census demographics (ACS 5-year)

| | |
| --- | --- |
| Source | US Census Bureau American Community Survey, 5-year estimates, 2020–2024 |
| URL | `https://api.census.gov/data/2024/acs/acs5` |
| Script | `src/collect/census_acs.py` |
| Downloaded | 2026-09-23 |
| Files | `data/raw/acs/acs2024_{tract,bg}_{la,king}.csv` |

Tables pulled: **B03002** (Hispanic or Latino origin by race) for total
population, Hispanic/Latino population and non-Hispanic white population;
**B01003** total population; **B19013** median household income.

| File | Rows | Population | % Hispanic/Latino |
| --- | --- | --- | --- |
| `acs2024_tract_la.csv` | 2,498 tracts | 9,808,667 | 48.4% |
| `acs2024_bg_la.csv` | 6,591 block groups | 9,808,667 | 48.4% |
| `acs2024_tract_king.csv` | 495 tracts | 2,287,171 | 11.0% |
| `acs2024_bg_king.csv` | 1,545 block groups | 2,287,171 | 11.0% |

**Limitations**

- ACS figures are 5-year survey estimates with margins of error, not a count.
  Margins are proportionally largest in small-population tracts and at block
  group level. Margins of error are not currently pulled; if a finding depends
  on small tracts, they should be.
- 2020–2024 is a five-year average, so it lags current conditions.
- Median household income is missing for 42 LA tracts and 2 King tracts
  (467 and 43 block groups respectively) — mostly very low population units,
  and the Census suppresses estimates it considers unreliable.
- 21 LA tracts and 1 King tract have zero population (industrial areas, parks,
  airports). They cannot have a meaningful "cameras per 10,000 residents".

---

## 2. Boundaries (TIGER/Line)

| | |
| --- | --- |
| Source | US Census Bureau TIGER/Line Shapefiles 2024 |
| URL | `https://www2.census.gov/geo/tiger/TIGER2024/{TRACT,BG}/` |
| Script | `src/collect/tiger_boundaries.py` |
| Downloaded | 2026-09-23 |
| Files | `data/raw/tiger/{tract,bg}_{la,king}.gpkg` and the source `.zip` files |

| File | Rows | Land area |
| --- | --- | --- |
| `tract_la.gpkg` | 2,498 | 10,516 sq km |
| `bg_la.gpkg` | 6,591 | 10,516 sq km |
| `tract_king.gpkg` | 495 | 5,480 sq km |
| `bg_king.gpkg` | 1,545 | 5,480 sq km |

Unit counts match the ACS tables exactly. `ALAND` (land area in square metres)
travels with these files and is the land-area source for population density.

**Limitations**

- TIGER boundaries are for mapping, not survey-grade.
- Note the URL path segment is lowercase `tiger`; the uppercase form returns 404.

---

## 3. ALPR cameras (OpenStreetMap / DeFlock)

| | |
| --- | --- |
| Source | OpenStreetMap via the Overpass API; data contributed largely by the DeFlock project |
| URL | `https://overpass-api.de/api/interpreter` |
| Script | `src/collect/flock_cameras.py` |
| Query date | **2026-09-23** |
| Files | `data/raw/osm/alpr_{la,king}.csv`, raw responses `alpr_{region}_2026-09-23.json` |

Tagging convention (per the OSM wiki and DeFlock): `man_made=surveillance` +
`surveillance:type=ALPR`, with vendor in `manufacturer` (sometimes `brand`) and
the owning agency in `operator`. The query pulls **all** ALPR features, not only
Flock ones, so the Flock share is measured rather than assumed. A camera counts
as Flock if "flock" appears in `manufacturer`, `brand`, `operator` or `name`.

| Region | In bounding box | Inside county | Flock | Flock share |
| --- | --- | --- | --- | --- |
| LA County | 5,394 | 3,594 | 2,586 | 72% |
| King County | 891 | 635 | 439 | 69% |

Most frequent Flock `operator` values — LA: no operator tag (2,218),
The Home Depot (72), Pasadena Police Department (61), Flock Safety (31),
Lowe's (26). King: no operator tag (286), The Home Depot (27), Lowe's (21),
Auburn Police (17), Flock Safety (14).

**Limitations — the most important in the project**

- **Crowdsourced and certainly incomplete.** Volunteers map cameras they
  notice. Coverage is likely better in areas with active contributors, which
  is itself a bias, and plausibly correlated with income and urbanity.
- **Under-counting is not random**, so a measured disparity may partly reflect
  where people looked rather than where cameras are.
- 86% of LA Flock cameras and 65% of King ones have no `operator` tag, so
  government-owned and privately owned cameras cannot be cleanly separated for
  most records. Private cameras are not placed by government and should not
  carry the same interpretation.
- The data changes continuously; these counts are a snapshot of 2026-09-23.
- Bounding-box queries were clipped to county polygons, so counts here are
  county-accurate, but a camera just outside a county line still watches
  traffic crossing it.

---

## 4. Arterial roads (OpenStreetMap)

| | |
| --- | --- |
| Source | OpenStreetMap via Overpass API |
| Script | `src/collect/osm_roads.py` |
| Query date | 2026-09-24 |
| Files | `data/raw/osm/roads_{la,king}.gpkg` |

`highway=primary|secondary|tertiary` plus their `_link` ramps, clipped to the
county polygon.

| Region | Ways in bbox | After clipping | Road-miles |
| --- | --- | --- | --- |
| LA County | 151,443 | 102,530 | 7,985 |
| King County | 31,135 | 24,949 | 2,374 |

**Limitations**

- Excludes residential and motorway classes by design: this is the arterial
  network where ALPR cameras are typically mounted. Cameras on residential
  streets or freeway ramps will be attributed to a tract whose arterial mileage
  does not explain them.
- OSM road classification varies by contributor; what one mapper calls
  tertiary another may call residential.

---

## 5. Retailers — Home Depot and Lowe's (OpenStreetMap)

| | |
| --- | --- |
| Source | OpenStreetMap via Overpass API |
| Script | `src/collect/osm_retailers.py` |
| Query date | 2026-09-24 |
| Files | `data/raw/osm/retailers_{la,king}.csv` |

Matched on `name`/`brand`/`operator` and restricted to home-improvement shop
types. Records within 100 m of another record of the same chain are collapsed,
because a store can be mapped as both a node and a building polygon.

| Region | Matches in bbox | Inside county | After dedup | Home Depot | Lowe's |
| --- | --- | --- | --- | --- | --- |
| LA County | 111 | 73 | 71 | 50 | 21 |
| King County | 34 | 24 | 21 | 13 | 8 |

**Limitations**

- OSM store coverage is good for large chains but not guaranteed complete;
  a missing store is a missing test case, not a zero.
- Chain-operated ALPR cameras appear in the camera data with `operator=The Home
  Depot` / `Lowe's`. These are **private** cameras. Phase 4 must separate
  private store cameras from government cameras near stores, or the retailer
  test measures the wrong thing.

---

## 6. Reported crime

| | |
| --- | --- |
| LA source | LAPD NIBRS Offenses Dataset, `data.lacity.org/resource/k7nn-b2ep` |
| Seattle source | SPD Crime Data 2008–Present, `data.seattle.gov/resource/tazs-3rd5` |
| Script | `src/collect/crime.py` |
| Downloaded | 2026-09-27 |
| Window | offences occurring 2025-01-01 onward |
| Files | `data/raw/crime/crime_{la,king}.csv` |

| Source | Rows downloaded | With usable coordinates | Date span |
| --- | --- | --- | --- |
| LAPD | 370,175 | 369,697 | 2025-01-01 to 2026-09-05 |
| Seattle PD | 133,028 | 111,584 | 2025-01-01 to 2026-09-26 |

Both departments publish NIBRS-coded offences, so crime categories are directly
comparable between the two cities.

**Limitations**

- **City, not county.** LAPD covers the City of Los Angeles (~3.8M of the
  county's 9.8M residents); SPD covers the City of Seattle (~750k of King
  County's 2.3M). Tracts outside those city limits have **no data**, which is
  not the same as no crime. Phase 3 marks them missing; Phase 4 must not treat
  missing as zero. Other agencies (LA County Sheriff, Bellevue PD, Kent PD and
  many more) publish separately or not at all.
- Seattle dropped 21,444 rows (16%) with placeholder 0,0 coordinates, which are
  typically suppressed-location offences. If suppression correlates with offence
  type or neighbourhood, this biases tract counts.
- LAPD coordinates are rounded to the "hundredth block", which is fine at tract
  level but not for precise proximity work.
- Reported crime measures reporting and police activity as well as crime.
  Areas with more policing can show more recorded crime, and ALPR cameras are
  themselves placed by police — a feedback loop the model cannot fully separate.
- The LAPD dataset contains junk dates as early as 1800 and Seattle as early as
  1900; the 2025-01-01 filter removes them.

---

## 7. City boundaries (TIGER/Line places)

| | |
| --- | --- |
| Source | US Census Bureau TIGER/Line Shapefiles 2024, PLACE layer |
| URL | `https://www2.census.gov/geo/tiger/TIGER2024/PLACE/` |
| Script | `src/collect/tiger_places.py` |
| Downloaded | 2026-09-27 |
| Files | `data/raw/tiger/city_{la,king}.gpkg` |

City of Los Angeles (GEOID 0644000, 1,219 sq km) and City of Seattle
(GEOID 5363000, 218 sq km). Used only to mark which tracts fall inside the
crime-reporting agency's jurisdiction, so that "no data" is not recorded as
"no crime". A unit counts as covered when more than half its area lies inside
the city.

---

## 8. Day-labor sites (candidates — unverified)

| | |
| --- | --- |
| Sources | NDLON "California Day Laborer Corners" map; City of Los Angeles Day Labor Program; Casa Latina (Seattle) |
| URLs | `https://ndlon.org/our-work/california-day-laborer-corners/`, `https://ewdd.lacity.gov/index.php/employment/day-labor`, `https://cid.lacity.gov/employment-services/day-labor-program`, `https://casa-latina.org/work/day-worker-center/` |
| Script | `src/collect/day_labor_sites.py` |
| Downloaded | 2026-09-27 |
| File | `data/raw/day_labor_sites.csv` |

| Region | Informal corners (NDLON) | Formal centers | Total |
| --- | --- | --- | --- |
| LA County | 68 | 6 | 74 |
| King County | 0 | 1 | 1 |

Street addresses without published coordinates were geocoded with the US Census
geocoder (`geocoding.geo.census.gov`, no key required).

**Limitations**

- **Every row is `verified=no`.** These are candidates from published lists, not
  confirmed active sites. Informal corners move, close and reopen.
- **King County has one site.** NDLON's map is California-only, and no
  equivalent published list was found for Washington. Searches surfaced only
  forum and review-site anecdotes about Home Depot lots in the Seattle area,
  which is not a citable source. **The Phase 4 day-labor test cannot be run for
  King County**, and Phase 4 must say so rather than reporting a result from
  n=1.
- NDLON's map has no published date, so entries may be years old.
- Formal city job centers and informal street corners are different phenomena;
  `site_type` distinguishes them and they should not be pooled uncritically.
