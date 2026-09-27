"""Arterial roads (OSM primary/secondary/tertiary) for both counties.

Used to compute arterial road-miles per tract, the main "fair explanation"
control: ALPR cameras are mounted on roads, so a tract with more arterial road
mileage should be expected to have more cameras.

Link roads (primary_link etc.) are included because they are part of the
arterial network. Geometry is fetched with `out geom` and written as lines.

Run: .venv/bin/python src/collect/osm_roads.py
Writes: data/raw/osm/roads_{region}.gpkg
"""

from __future__ import annotations

import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

from common import RAW, REGIONS, overpass, stamp

QUERY = """
[out:json][timeout:600];
way["highway"~"^(primary|secondary|tertiary)(_link)?$"]({bbox});
out geom;
"""


def main() -> int:
    outdir = RAW / "osm"
    outdir.mkdir(parents=True, exist_ok=True)
    today = stamp()

    for region in REGIONS:
        print(f"{region.label}: querying Overpass for arterial roads")
        elements = overpass(QUERY, region.bbox).get("elements", [])

        rows, geoms = [], []
        for el in elements:
            geom = el.get("geometry") or []
            if len(geom) < 2:
                continue
            tags = el.get("tags", {})
            geoms.append(LineString([(p["lon"], p["lat"]) for p in geom]))
            rows.append(
                {
                    "osm_id": el["id"],
                    "highway": tags.get("highway"),
                    "name": tags.get("name"),
                    "lanes": tags.get("lanes"),
                    "maxspeed": tags.get("maxspeed"),
                    "region": region.key,
                    "query_date": today,
                }
            )

        gdf = gpd.GeoDataFrame(pd.DataFrame(rows), geometry=geoms, crs="EPSG:4326")

        # Clip to the county polygon so bbox overspill does not inflate mileage.
        tracts = gpd.read_file(RAW / "tiger" / f"tract_{region.key}.gpkg").to_crs(4326)
        clipped = gpd.clip(gdf, tracts.union_all())
        clipped = clipped[~clipped.geometry.is_empty & clipped.geometry.notna()]

        miles = clipped.to_crs(region.crs).length.sum() / 5280.0
        out = outdir / f"roads_{region.key}.gpkg"
        clipped.to_file(out, driver="GPKG", layer="roads")

        by_class = clipped["highway"].value_counts().to_dict()
        print(f"  {len(gdf):,} ways in bbox, {len(clipped):,} after clipping to county")
        print(f"  {miles:,.0f} arterial road-miles; by class: {by_class}")
        print(f"  -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
