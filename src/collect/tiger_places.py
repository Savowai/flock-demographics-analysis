"""City boundaries (TIGER/Line places).

Two uses:

1. `city_{region}.gpkg` - just Los Angeles and Seattle. Crime data comes from
   LAPD and SPD, which police those cities only, so Phase 3 needs them to
   distinguish "outside the reporting city, so no data" from "inside the city
   and genuinely low crime".
2. `places_{region}.gpkg` - every incorporated place in the county. Flock is
   purchased city by city, so Phase 4 tests city-level adoption: does a city's
   demographic profile predict whether it deployed cameras at all? Land not
   inside any place is unincorporated county.

Run: .venv/bin/python src/collect/tiger_places.py
Writes: data/raw/tiger/city_{la,king}.gpkg, data/raw/tiger/places_{la,king}.gpkg
"""

from __future__ import annotations

import sys

import geopandas as gpd

from common import RAW, REGION_BY_KEY, TIGER_YEAR, download

BASE = f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}"

CITIES = {
    "la": {"state": "06", "name": "Los Angeles", "lsad": "25"},    # 25 = city
    "king": {"state": "53", "name": "Seattle", "lsad": "25"},
}


def main() -> int:
    outdir = RAW / "tiger"
    outdir.mkdir(parents=True, exist_ok=True)

    for region_key, cfg in CITIES.items():
        rel = f"PLACE/tl_{TIGER_YEAR}_{cfg['state']}_place.zip"
        zip_path = outdir / rel.split("/")[-1]
        download(f"{BASE}/{rel}", zip_path)

        gdf = gpd.read_file(zip_path)
        match = gdf[(gdf["NAME"] == cfg["name"]) & (gdf["LSAD"] == cfg["lsad"])]
        if len(match) != 1:
            print(f"  WARNING: {len(match)} matches for {cfg['name']}, expected 1")
            if match.empty:
                continue

        out = outdir / f"city_{region_key}.gpkg"
        match.to_file(out, driver="GPKG", layer="city")
        print(
            f"  {cfg['name']}: GEOID {match.iloc[0]['GEOID']}, "
            f"land area {match.iloc[0]['ALAND'] / 1e6:,.0f} sq km -> {out.name}"
        )

        # All incorporated places whose centre falls in the county.
        region = REGION_BY_KEY[region_key]
        tracts = gpd.read_file(RAW / "tiger" / f"tract_{region_key}.gpkg")
        county = tracts.to_crs(region.crs).union_all()

        places = gdf.to_crs(region.crs)
        in_county = places[places.representative_point().within(county)].copy()
        in_county = in_county[["GEOID", "NAME", "NAMELSAD", "LSAD", "ALAND",
                               "geometry"]]

        places_out = outdir / f"places_{region_key}.gpkg"
        in_county.to_file(places_out, driver="GPKG", layer="places")
        print(
            f"  {len(in_county)} incorporated places in the county "
            f"-> {places_out.name}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
