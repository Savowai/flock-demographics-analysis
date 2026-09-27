# Manual downloads and verification needed

Things a script could not get, or could not confirm. Nothing here has been
silently skipped.

## Needs your verification (Phase 2 output)

### `data/raw/day_labor_sites.csv` — 75 candidate sites, all `verified=no`

Every row came from a published list, not from observation. Set `verified` to
`yes` or `no` per row, and use the `notes` column for anything relevant
(for example "closed 2023", "moved across the street").

- **LA County: 74 candidates** — 68 informal corners from the NDLON map,
  6 formal City of Los Angeles job centers.
- **King County: 1 candidate** — Casa Latina Day Worker Center, Seattle.

### King County day-labor sites — not found in any citable source

NDLON's corner map covers California only. Searches for a Washington equivalent
turned up only forum posts and review-site comments about Home Depot lots in
Seattle, Bellevue, Kent, Renton and Burien. Those are not usable sources.

Consequence: **the day-labor portion of the Phase 4 retailer test cannot be run
for King County.** The Home Depot/Lowe's camera comparison still runs for both
regions; only the day-labor split is LA-only.

If you can obtain any of these, the test becomes possible:

- Casa Latina or Seattle Office of Labor Standards internal site lists
- King County or City of Seattle records on informal hiring sites
- Academic work on Puget Sound day labor (e.g. University of Washington
  labor studies)

## Blocked by the publisher

| Source | Problem | Workaround used |
| --- | --- | --- |
| `ewdd.lacity.gov/index.php/employment/day-labor` | Returns HTTP 403 to automated fetchers | Addresses transcribed from search-result text, then geocoded. **Worth a manual check against the live page.** |
| `cid.lacity.gov/employment-services/day-labor-program` | HTTP 403 | Same |

## Expected for Phase 6 (documents)

Anticipated to need manual retrieval when document collection starts:

- Paywalled investigative reporting (e.g. some 404 Media and local outlet
  coverage)
- Public records responses that were released as images or by request only
- Agency contracts not posted publicly

This list will be updated as Phase 6 runs.
