"""City boundaries for Los Angeles and Seattle (TIGER/Line places).

Crime data comes from LAPD and SPD, which police the cities only. These
polygons let Phase 3 distinguish "outside the reporting city, so no data" from
"inside the city and genuinely low crime".

Run: .venv/bin/python src/collect/tiger_places.py
Writes: data/raw/tiger/city_{la,king}.gpkg
"""

from __future__ import annotations

import sys

import geopandas as gpd

from common import RAW, TIGER_YEAR, download

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
