# Findings

What the data shows, in plain English, with the numbers behind it and the
reasons to be careful. Result tables are in `outputs/tables/`.

**Read this first.** Camera locations come from a crowdsourced map. Volunteers
record cameras they notice, so the data is certainly incomplete, and the gaps
are probably not random. Everything below describes *mapped* cameras. Nothing
below establishes anyone's intent.

---

## The short version

1. **The two regions point in opposite directions.** In King County, more
   Hispanic neighbourhoods have substantially more cameras. In LA County they
   have slightly fewer. The same analysis, run the same way, gives opposite
   answers in the two places, so there is no single "Flock targets Latino
   neighbourhoods" finding here.
2. **The strongest and most consistent result is not about neighbourhoods at
   all.** Home Depot and Lowe's are about five times more likely than
   comparable big-box stores to have a Flock camera - one not owned by the
   chain - within 150 metres. That holds in both regions.
3. **Cities almost all adopted Flock.** 81 of 88 LA cities and 25 of 31 King
   County cities have mapped non-retail Flock cameras, so "which cities bought
   in" barely varies and cannot carry a demographic story.

---

## 1. Raw comparison by neighbourhood (`descriptive_quartiles.csv`)

Tracts sorted into four groups by Hispanic/Latino share, cameras counted per
arterial road-mile (cameras go on roads, so this is the fairest simple
denominator).

**Los Angeles County**

| Quartile | Hispanic share | Cameras | Per road-mile | Per 10k residents |
| --- | --- | --- | --- | --- |
| 1 (least) | 0-21% | 919 | 0.437 | 3.94 |
| 2 | 21-45% | 586 | 0.245 | 2.42 |
| 3 | 45-72% | 543 | 0.297 | 2.14 |
| 4 (most) | 72-100% | 501 | 0.333 | 2.01 |

The most Hispanic quartile has **0.76x** the camera density of the least - that
is, about 24% fewer per road-mile.

**King County**

| Quartile | Hispanic share | Cameras | Per road-mile | Per 10k residents |
| --- | --- | --- | --- | --- |
| 1 (least) | 0-5% | 63 | 0.124 | 1.20 |
| 2 | 5-9% | 66 | 0.104 | 1.14 |
| 3 | 9-13% | 106 | 0.166 | 1.79 |
| 4 (most) | 13-59% | 204 | 0.343 | 3.45 |

The most Hispanic quartile has **2.76x** the camera density of the least.

Note how different the two counties are to begin with: LA County is 48%
Hispanic overall, King County 11%. "Most Hispanic quartile" means 72-100% in LA
and 13-59% in King. These are not the same comparison.

Reported crime is nearly flat across LA quartiles (89-101 offences per 1,000
residents), so crime differences do not explain the LA pattern.

---

## 2. Regression (`model_summary.csv`, `model_coefficients.csv`)

Negative binomial models of camera count per tract, with arterial road-miles as
an offset (so the model predicts cameras *per road-mile*), controlling for
population, median household income and population density. The outcome
excludes cameras operated by Home Depot and Lowe's, which are private.

Read the numbers as: effect of each **10 percentage point** increase in
Hispanic/Latino share.

| Model | LA County | King County |
| --- | --- | --- |
| M1 base | **-4.2%** (p=0.040) | **+45.8%** (p=0.006) |
| M2 + crime control | -13.7% (p=0.014) | +58.8% (p=0.426) |
| M3 within-city | -6.3% (p=0.008) | +30.3% (p=0.035) |
| M4 block group | -3.1% (p=0.035) | +24.2% (p<0.001) |

**M3 is the most useful model.** It compares neighbourhoods policed by the same
department, which removes the effect of which city bought cameras. The King
County effect survives it: within the same city, a neighbourhood 10 points more
Hispanic has about **30% more cameras per road-mile**. In LA the effect stays
slightly negative.

M2 shows the LA effect getting more negative when crime is controlled, but it
covers only the 1,087 tracts inside the City of LA. King County's M2 covers 176
tracts and is not statistically significant - too small to conclude from.

---

## 3. Spatial checks (`spatial_diagnostics.csv`)

Camera counts clump geographically, so tracts are not independent observations
and plain regression overstates confidence.

Moran's I on the M1 residuals: **0.154 in LA, 0.142 in King** (both p=0.001).
Both are clustered, so a spatial lag model was fitted as a cross-check.

| | Spatial lag coefficient | p | rho (neighbour influence) |
| --- | --- | --- | --- |
| LA County | -0.010 | 0.039 | 0.454 |
| King County | +0.133 | <0.001 | 0.398 |

The directions and significance survive. Rho of 0.4-0.45 is substantial: a
tract's camera count really does depend heavily on its neighbours', which is
what you would expect if cameras are deployed in batches by agencies.

Caveat: the spatial lag model is fitted on log(cameras + 1) rather than as a
count model, because a spatial-lag negative binomial is not available in the
library used. It is a check on direction, not a replacement.

---

## 4. City-level adoption (`city_adoption_models.csv`, `city_profiles.csv`)

Testing whether cities with more Hispanic residents were more likely to buy
Flock, treating each city as one observation.

**This test is largely uninformative, because adoption is nearly universal.**

| | Cities | With cameras | Mean Hispanic share, adopters | Non-adopters |
| --- | --- | --- | --- | --- |
| LA County | 88 | 81 | 44.9% | 46.8% |
| King County | 31 | 25 | 11.2% | 10.8% |

Adopters and non-adopters look demographically the same. Logistic models find
nothing: LA odds ratio 0.96 (p=0.842), King 1.02 (p=0.984).

Camera *intensity* given adoption is a different matter. In King County, city
camera count per road-mile rises with Hispanic share (rate ratio 2.82 per 10
points, p=0.054 - borderline). In LA it does not (0.94, p=0.253).

The cities with the highest camera density make the point that this is not a
simple demographic story:

| LA County | Hispanic | Cameras/mile | | King County | Hispanic | Cameras/mile |
| --- | --- | --- | --- | --- | --- | --- |
| West Hollywood | 13% | 3.22 | | Yarrow Point | 3% | 1.60 |
| San Fernando | 92% | 2.40 | | Medina | 0.3% | 1.27 |
| La Puente | 79% | 2.35 | | SeaTac | 23% | 0.95 |
| Beverly Hills | 8% | 2.24 | | Renton | 16% | 0.80 |
| Hawaiian Gardens | 76% | 2.11 | | Tukwila | 26% | 0.77 |

Very wealthy, very white cities (Beverly Hills, San Marino, Medina, Yarrow
Point) and heavily Latino working-class cities (San Fernando, La Puente,
Hawaiian Gardens) both saturate themselves with cameras. Wealth buys
surveillance too.

**Important limitation:** a camera inside a city's limits was not necessarily
bought by that city. Sheriffs, transit agencies, HOAs and businesses deploy
them too, and 86% of LA's mapped Flock cameras have no operator tag.

---

## 5. Retailer test (`retailer_camera_proximity.csv`, `retailer_daylabor_comparison.csv`)

For every Home Depot and Lowe's, whether a Flock camera sits within 150 m,
compared against a control group of big-box stores that are not day-labor
hiring sites (Target, Walmart, Costco, Best Buy, Kohl's).

Counting only cameras **not** operated by the chain itself:

| | Home improvement | Control big-box | Odds ratio | p |
| --- | --- | --- | --- | --- |
| LA County | 46% of 71 | 14% of 196 | **5.21** | <0.001 |
| King County | 43% of 21 | 11% of 35 | **5.81** | 0.010 |

**This is the most consistent finding in the project.** Home improvement stores
are about five times more likely than comparable big-box stores - similar size,
similar parking lots, similar arterial roads - to have someone else's ALPR
camera next to them. The effect is nearly identical in two very different
counties.

Including the chains' own cameras, 82% of LA and 86% of King County home
improvement stores have a Flock camera within 150 m.

What this does **not** establish: who placed those cameras, or why. Home
improvement stores differ from Target in ways beyond day labor - tool theft,
lumber yards, contractor traffic, longer hours. The pattern is real and
replicated; the explanation is not settled by this data.

**The day-labor comparison could not be run.** It needs verified day-labor
sites, and `data/raw/day_labor_sites.csv` currently has 74 unverified
candidates for LA and 1 for King County. No citable published list of
Washington day-labor sites was found (see `docs/manual_downloads.md`). Verify
sites in that file and the test runs automatically.

---

## Limitations

**The camera data is crowdsourced and incomplete.** This is the binding
constraint on everything above. DeFlock volunteers map what they find.
Coverage probably varies with how many privacy-minded contributors live in an
area, which could correlate with income, education and urbanity. If mapping is
denser in wealthier areas, the LA result could be an artifact of who was
looking. Nothing in this project can rule that out.

**Private cameras are not government placements.** 98 LA and 48 King County
Flock cameras are operated by Home Depot or Lowe's, and are excluded from the
models. But 86% of LA's Flock cameras carry no operator tag at all, so
government and private cameras cannot be cleanly separated for most records.

**Crime data covers cities, not counties.** LAPD polices 3.8M of LA County's
9.8M residents; SPD 750k of King County's 2.3M. Only 44% of LA tracts and 36%
of King tracts have any crime data. Tracts outside are recorded as missing, not
zero. Reported crime also measures policing intensity, not just crime - and
cameras are placed by police, so there is feedback the model cannot untangle.

**Disparity is not intent.** Even a large, robust placement disparity would not
show that anyone chose locations because of who lives there. Cameras follow
roads, commercial corridors, traffic volume and municipal budgets, all of which
correlate with demographics for reasons that predate ALPR by decades.

**ACS estimates carry margins of error** that are widest in exactly the small
tracts where camera counts are most volatile. Margins were not incorporated.

**One snapshot.** Cameras were queried on 2026-09-23. Deployments change
constantly, and this cannot show trends over time.

**The two counties are not comparable units.** LA County is 48% Hispanic with
10M residents across 88 cities; King County is 11% Hispanic with 2.3M across
38. Quartiles mean different things in each.

---

## What would strengthen this

- **Verified day-labor sites**, which unlocks the test the project was designed
  around.
- **Public records requests** for actual agency camera inventories, which would
  replace crowdsourced locations with authoritative ones and settle the
  completeness problem.
- **Operator identification** for the untagged 86%, separating government from
  private cameras.
- **Time series**, to see whether deployment patterns shifted with immigration
  enforcement activity.
- **The document record** (Phase 6), which speaks to a different question the
  coordinates cannot answer: who gets access to what these cameras collect.
