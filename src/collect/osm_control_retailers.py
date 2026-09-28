"""Control retailers: big-box stores that are NOT day-labor hiring sites.

"82% of Home Depots have a Flock camera within 150 m" is uninterpretable on
its own - big-box stores sit on arterial roads in commercial strips, exactly
where ALPR cameras go. This collects a comparison group of similarly sized
retailers with large parking lots on similar roads (Target, Walmart, Costco,
Best Buy, Kohl's) so the Home Depot/Lowe's rate has something to be measured
against.

Run: .venv/bin/python src/collect/osm_control_retailers.py
Writes: data/raw/osm/control_retailers_{region}.csv
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
  nwr["name"~"target|walmart|costco|best buy|kohl's|kohls",i]["shop"]({bbox});
  nwr["brand"~"target|walmart|costco|best buy|kohl's|kohls",i]["shop"]({bbox});
);
out center tags;
"""

CHAINS = {
    "Target": re.compile(r"\btarget\b", re.IGNORECASE),
    "Walmart": re.compile(r"walmart", re.IGNORECASE),
    "Costco": re.compile(r"costco", re.IGNORECASE),
    "Best Buy": re.compile(r"best\s*buy", re.IGNORECASE),
    "Kohl's": re.compile(r"kohl'?s", re.IGNORECASE),
}

VALID_SHOP = {"department_store", "supermarket", "wholesale", "electronics",
              "clothes", "variety_store"}


def main() -> int:
    outdir = RAW / "osm"
    today = stamp()

    for region in REGIONS:
        print(f"{region.label}: querying Overpass for control retailers")
        elements = overpass(QUERY, region.bbox).get("elements", [])

        rows = []
        for el in elements:
            tags = el.get("tags", {})
            lat = el.get("lat", (el.get("center") or {}).get("lat"))
            lon = el.get("lon", (el.get("center") or {}).get("lon"))
            if lat is None or lon is None:
                continue
            haystack = " ".join(str(tags.get(k, "")) for k in ("name", "brand"))
            chain = next((c for c, rx in CHAINS.items() if rx.search(haystack)), None)
            if chain is None:
                continue
            if tags.get("shop") not in VALID_SHOP:
                continue
            rows.append(
                {
                    "chain": chain,
                    "osm_type": el["type"],
                    "osm_id": el["id"],
                    "lat": lat,
                    "lon": lon,
                    "name": tags.get("name"),
                    "shop": tags.get("shop"),
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

        proj = inside.to_crs(region.crs)
        keep, used = [], []
        for idx, geom in zip(proj.index, proj.geometry):
            chain = proj.at[idx, "chain"]
            if any(geom.distance(g) < 328 and c == chain for g, c in used):
                continue
            used.append((geom, chain))
            keep.append(idx)
        deduped = inside.loc[keep].copy()
        deduped["region"] = region.key
        deduped["query_date"] = today

        out = outdir / f"control_retailers_{region.key}.csv"
        deduped.drop(columns="geometry").to_csv(out, index=False)
        print(f"  {len(deduped)} stores after dedup: "
              f"{deduped['chain'].value_counts().to_dict()} -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
