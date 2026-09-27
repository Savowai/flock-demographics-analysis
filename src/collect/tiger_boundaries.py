"""TIGER/Line tract and block-group boundaries for LA County and King County.

TIGER ships one file per state, so we download the state file and keep only the
county's units. ALAND (land area, square metres) travels with these files and is
the land-area source for the density calculations.

Run: .venv/bin/python src/collect/tiger_boundaries.py
Writes: data/raw/tiger/*.zip (as downloaded) and
        data/raw/tiger/{tract|bg}_{region}.gpkg (county subset)
"""

from __future__ import annotations

import sys

import geopandas as gpd

from common import PROJECT_ROOT, RAW, REGIONS, TIGER_YEAR, download

# Note: the path segment is lowercase "tiger"; the uppercase form 404s.
BASE = f"https://www2.census.gov/geo/tiger/TIGER{TIGER_YEAR}"

LAYERS = {
    "tract": "TRACT/tl_{year}_{state}_tract.zip",
    "bg": "BG/tl_{year}_{state}_bg.zip",
}


def main() -> int:
    outdir = RAW / "tiger"
    outdir.mkdir(parents=True, exist_ok=True)

    for region in REGIONS:
        for level, pattern in LAYERS.items():
            rel = pattern.format(year=TIGER_YEAR, state=region.state_fips)
            zip_path = outdir / rel.split("/")[-1]
            download(f"{BASE}/{rel}", zip_path)

            gdf = gpd.read_file(zip_path)
            county = gdf[
                (gdf["STATEFP"] == region.state_fips)
                & (gdf["COUNTYFP"] == region.county_fips)
            ].copy()
            county = county[["GEOID", "ALAND", "AWATER", "INTPTLAT", "INTPTLON", "geometry"]]
            county["land_sqkm"] = county["ALAND"] / 1e6

            out = outdir / f"{level}_{region.key}.gpkg"
            county.to_file(out, driver="GPKG", layer=level)
            print(
                f"{region.label} {level}: {len(county):,} of {len(gdf):,} statewide, "
                f"CRS {county.crs.to_string()}, "
                f"land area {county['land_sqkm'].sum():,.0f} sq km, "
                f"{int(county.geometry.isna().sum())} missing geometries -> {out.name}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
