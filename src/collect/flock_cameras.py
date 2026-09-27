"""ALPR camera locations from OpenStreetMap via the Overpass API.

DeFlock volunteers map ALPR cameras into OSM as:
    man_made=surveillance + surveillance:type=ALPR
with the vendor in `manufacturer` (e.g. "Flock Safety"; `brand` is also seen in
the wild) and the owning agency in `operator`.

This script pulls EVERY ALPR feature in each county's bounding box, not just
Flock ones, so the Flock share can be measured rather than assumed. Flock is
flagged by a case-insensitive "flock" match on manufacturer/brand/operator/name.

Camera data changes often, so the query date is stored in every row and in the
raw response filename.

Run: .venv/bin/python src/collect/flock_cameras.py
Writes: data/raw/osm/alpr_{region}_{date}.json  (raw Overpass response)
        data/raw/osm/alpr_{region}.csv          (flattened, county-clipped)
"""

from __future__ import annotations

import json
import re
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from common import RAW, REGIONS, overpass, stamp

FLOCK_RE = re.compile(r"flock", re.IGNORECASE)

QUERY = """
[out:json][timeout:300];
(
  node["surveillance:type"="ALPR"]({bbox});
  way["surveillance:type"="ALPR"]({bbox});
  node["man_made"="surveillance"]["manufacturer"~"flock",i]({bbox});
  way["man_made"="surveillance"]["manufacturer"~"flock",i]({bbox});
  node["man_made"="surveillance"]["brand"~"flock",i]({bbox});
  way["man_made"="surveillance"]["brand"~"flock",i]({bbox});
);
out center tags;
"""


def flatten(payload: dict) -> pd.DataFrame:
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat", (el.get("center") or {}).get("lat"))
        lon = el.get("lon", (el.get("center") or {}).get("lon"))
        if lat is None or lon is None:
            continue
        vendor_fields = " ".join(
            str(tags.get(k, ""))
            for k in ("manufacturer", "brand", "operator", "name")
        )
        rows.append(
            {
                "osm_type": el["type"],
                "osm_id": el["id"],
                "lat": lat,
                "lon": lon,
                "manufacturer": tags.get("manufacturer"),
                "brand": tags.get("brand"),
                "operator": tags.get("operator"),
                "name": tags.get("name"),
                "surveillance_type": tags.get("surveillance:type"),
                "surveillance": tags.get("surveillance"),
                "surveillance_zone": tags.get("surveillance:zone"),
                "direction": tags.get("direction"),
                "is_flock": bool(FLOCK_RE.search(vendor_fields)),
                "all_tags": json.dumps(tags, sort_keys=True),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    outdir = RAW / "osm"
    outdir.mkdir(parents=True, exist_ok=True)
    today = stamp()

    for region in REGIONS:
        print(f"{region.label}: querying Overpass for ALPR features")
        payload = overpass(QUERY, region.bbox)

        raw_path = outdir / f"alpr_{region.key}_{today}.json"
        raw_path.write_text(json.dumps(payload))

        df = flatten(payload)
        if df.empty:
            print(f"  WARNING: no ALPR features returned for {region.label}")
            continue

        # Clip the bounding box down to the actual county polygon.
        tracts = gpd.read_file(RAW / "tiger" / f"tract_{region.key}.gpkg")
        county = tracts.union_all()
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
            crs="EPSG:4269",
        )
        inside = gdf[gdf.within(county)].copy()
        inside["region"] = region.key
        inside["query_date"] = today

        out = outdir / f"alpr_{region.key}.csv"
        inside.drop(columns="geometry").to_csv(out, index=False)

        flock = int(inside["is_flock"].sum())
        operators = (
            inside.loc[inside["is_flock"], "operator"].fillna("(no operator tag)")
            .value_counts()
        )
        print(
            f"  {len(df):,} ALPR features in bbox, {len(inside):,} inside the county, "
            f"{flock:,} Flock ({100 * flock / max(len(inside), 1):.0f}%)"
        )
        print(f"  top Flock operators: "
              f"{', '.join(f'{k} ({v})' for k, v in operators.head(5).items())}")
        print(f"  -> {out.name} (raw: {raw_path.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
