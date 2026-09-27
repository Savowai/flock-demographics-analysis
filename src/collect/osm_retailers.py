"""Home Depot and Lowe's store locations from OpenStreetMap.

These two chains are the Phase 4 retailer test: both are common informal
day-labor hiring sites, and Flock cameras are known to be installed on some
store lots. Stores are matched on name/brand/operator rather than on a single
tag, because OSM tagging of chains is inconsistent, and both nodes and building
polygons are used (polygons reduced to their centroid).

Run: .venv/bin/python src/collect/osm_retailers.py
Writes: data/raw/osm/retailers_{region}.csv
"""

from __future__ import annotations

import json
import re
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from common import RAW, REGIONS, overpass, stamp

QUERY = """
[out:json][timeout:300];
(
  nwr["name"~"home depot",i]["shop"]({bbox});
  nwr["name"~"lowe's|lowes",i]["shop"]({bbox});
  nwr["brand"~"home depot|lowe's|lowes",i]({bbox});
  nwr["operator"~"home depot|lowe's|lowes",i]["shop"]({bbox});
);
out center tags;
"""

CHAINS = {
    "Home Depot": re.compile(r"home\s*depot", re.IGNORECASE),
    "Lowe's": re.compile(r"lowe'?s", re.IGNORECASE),
}

# Chains sell more than DIY; keep only the actual home-improvement stores.
VALID_SHOP = {"doityourself", "hardware", "trade", "garden_centre", "department_store"}


def main() -> int:
    outdir = RAW / "osm"
    outdir.mkdir(parents=True, exist_ok=True)
    today = stamp()

    for region in REGIONS:
        print(f"{region.label}: querying Overpass for Home Depot / Lowe's")
        elements = overpass(QUERY, region.bbox).get("elements", [])

        rows = []
        for el in elements:
            tags = el.get("tags", {})
            lat = el.get("lat", (el.get("center") or {}).get("lat"))
            lon = el.get("lon", (el.get("center") or {}).get("lon"))
            if lat is None or lon is None:
                continue

            haystack = " ".join(
                str(tags.get(k, "")) for k in ("name", "brand", "operator")
            )
            chain = next((c for c, rx in CHAINS.items() if rx.search(haystack)), None)
            if chain is None:
                continue
            shop = tags.get("shop")
            if shop is not None and shop not in VALID_SHOP:
                continue

            rows.append(
                {
                    "chain": chain,
                    "osm_type": el["type"],
                    "osm_id": el["id"],
                    "lat": lat,
                    "lon": lon,
                    "name": tags.get("name"),
                    "shop": shop,
                    "addr": " ".join(
                        filter(
                            None,
                            [
                                tags.get("addr:housenumber"),
                                tags.get("addr:street"),
                                tags.get("addr:city"),
                            ],
                        )
                    )
                    or None,
                    "all_tags": json.dumps(tags, sort_keys=True),
                }
            )

        df = pd.DataFrame(rows)
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
            crs="EPSG:4326",
        )

        tracts = gpd.read_file(RAW / "tiger" / f"tract_{region.key}.gpkg").to_crs(4326)
        inside = gdf[gdf.within(tracts.union_all())].copy()

        # One store can be mapped as both a node and a building polygon; collapse
        # anything within 100 m of another record of the same chain.
        proj = inside.to_crs(region.crs)
        keep, used = [], []
        for idx, geom in zip(proj.index, proj.geometry):
            chain = proj.at[idx, "chain"]
            if any(
                geom.distance(g) < 328 and c == chain for g, c in used
            ):  # 328 ft ~ 100 m
                continue
            used.append((geom, chain))
            keep.append(idx)
        deduped = inside.loc[keep].copy()
        deduped["region"] = region.key
        deduped["query_date"] = today

        out = outdir / f"retailers_{region.key}.csv"
        deduped.drop(columns="geometry").to_csv(out, index=False)
        counts = deduped["chain"].value_counts().to_dict()
        print(
            f"  {len(df):,} matches in bbox, {len(inside):,} inside county, "
            f"{len(deduped):,} after deduplication: {counts} -> {out.name}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
