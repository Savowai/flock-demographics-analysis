"""Candidate day-labor sites for LA County and King County.

Three sources, all published:

1. NDLON (National Day Laborer Organizing Network) "California Day Laborer
   Corners" map - informal street-corner hiring sites with coordinates.
   California only, so it contributes nothing for King County.
2. City of Los Angeles Day Labor Program - the official municipal day labor
   centers (EWDD / Community Investment Department pages).
3. Casa Latina (Seattle) - the main formal day worker center in King County.

Everything is written with verified="no". These are CANDIDATES. Street-corner
sites move, close and reopen, and a published list is not evidence that a site
is active today. The user verifies before any of this is used in analysis.

Addresses without coordinates are geocoded with the US Census geocoder (free,
no key required).

Run: .venv/bin/python src/collect/day_labor_sites.py
Writes: data/raw/day_labor_sites.csv
"""

from __future__ import annotations

import json
import re
import sys
import time

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from common import RAW, REGIONS, session, stamp

NDLON_URL = "https://ndlon.org/our-work/california-day-laborer-corners/"

# Official City of Los Angeles day labor centers. Addresses transcribed from the
# EWDD and Community Investment Department program pages (both listed in
# docs/data_sources.md); coordinates come from the Census geocoder below.
LA_CITY_CENTERS = [
    ("Cypress Park Community Job Center (IDEPSCA)",
     "2055 N Figueroa St, Los Angeles, CA 90065"),
    ("Downtown / Fashion District Job Center (IDEPSCA)",
     "121 E Pico Blvd, Los Angeles, CA 90015"),
    ("Wilmington Community Job Center (IDEPSCA)",
     "1301 N Figueroa St, Wilmington, CA 90744"),
    ("Hollywood Community Job Center (IDEPSCA)",
     "5107 W Sunset Blvd, Los Angeles, CA 90027"),
    ("North Hollywood Day Labor Center",
     "11839 Sherman Way, North Hollywood, CA 91605"),
    ("Hollywood Community Job Center - De Longpre",
     "5669 W De Longpre Ave, Los Angeles, CA 90028"),
]

KING_COUNTY_CENTERS = [
    ("Casa Latina Day Worker Center", "317 17th Ave S, Seattle, WA 98144"),
]

GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def extract_json_array(text: str, key: str) -> list[dict]:
    """Pull a balanced JSON array that follows `"key":` out of a page."""
    start = text.find(f'"{key}":[')
    if start == -1:
        return []
    start = text.index("[", start)
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    return []


def fetch_ndlon() -> pd.DataFrame:
    with session() as s:
        resp = s.get(NDLON_URL, timeout=120)
    resp.raise_for_status()

    # The page HTML-escapes ampersands inside the embedded config blob.
    places = extract_json_array(resp.text.replace("&#038;", "&"), "places")
    rows = []
    for p in places:
        loc = p.get("location") or {}
        try:
            lat, lon = float(loc["lat"]), float(loc["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(
            {
                "name": (p.get("title") or "").strip(),
                "address": (p.get("address") or "").strip(),
                "lat": lat,
                "lon": lon,
                "source": f"NDLON California Day Laborer Corners map ({NDLON_URL})",
                "site_type": "informal corner (NDLON map)",
            }
        )
    print(f"  NDLON: {len(places)} places on the map, {len(rows)} with coordinates")
    return pd.DataFrame(rows)


def geocode(address: str) -> tuple[float | None, float | None]:
    params = {"address": address, "benchmark": "Public_AR_Current", "format": "json"}
    with session() as s:
        for attempt in range(3):
            try:
                r = s.get(GEOCODER, params=params, timeout=60)
                r.raise_for_status()
                matches = r.json()["result"]["addressMatches"]
                if matches:
                    c = matches[0]["coordinates"]
                    return float(c["y"]), float(c["x"])
                return None, None
            except Exception as exc:
                if attempt == 2:
                    print(f"    geocode failed for {address}: {exc}")
                    return None, None
                time.sleep(3)
    return None, None


def centers_frame(entries, source_label, site_type) -> pd.DataFrame:
    rows = []
    for name, address in entries:
        lat, lon = geocode(address)
        rows.append(
            {
                "name": name,
                "address": address,
                "lat": lat,
                "lon": lon,
                "source": source_label,
                "site_type": site_type,
            }
        )
        print(f"    {'OK ' if lat else 'NO COORDS'} {name}")
    return pd.DataFrame(rows)


def main() -> int:
    print("Collecting day-labor site candidates")
    frames = [
        fetch_ndlon(),
        centers_frame(
            LA_CITY_CENTERS,
            "City of Los Angeles Day Labor Program "
            "(ewdd.lacity.gov/index.php/employment/day-labor; "
            "cid.lacity.gov/employment-services/day-labor-program)",
            "formal city job center",
        ),
        centers_frame(
            KING_COUNTY_CENTERS,
            "Casa Latina Day Worker Center (casa-latina.org/work/day-worker-center/)",
            "formal worker center",
        ),
    ]
    df = pd.concat(frames, ignore_index=True).dropna(subset=["lat", "lon"])

    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )

    # Keep only points inside our two study counties.
    kept = []
    for region in REGIONS:
        tracts = gpd.read_file(RAW / "tiger" / f"tract_{region.key}.gpkg").to_crs(4326)
        inside = gdf[gdf.within(tracts.union_all())].copy()
        inside["region"] = region.key
        print(f"  {region.label}: {len(inside)} candidate sites inside the county")
        kept.append(inside)

    out_df = pd.concat(kept, ignore_index=True)
    out_df["verified"] = "no"
    out_df["date_retrieved"] = stamp()
    out_df["notes"] = ""

    out = RAW / "day_labor_sites.csv"
    columns = ["name", "address", "lat", "lon", "source", "verified",
               "site_type", "region", "date_retrieved", "notes"]
    out_df[columns].sort_values(["region", "name"]).to_csv(out, index=False)
    print(f"\n  {len(out_df)} candidates written to {out.name}, all verified=no")
    print("  Verify each site before it is used in Phase 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
