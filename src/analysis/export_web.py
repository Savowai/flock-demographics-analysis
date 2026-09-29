"""Phase 7.1: export static artifacts for the web app.

Everything the site needs, small enough to serve from a CDN:

  tracts_{region}.geojson   simplified tract polygons + the analysis columns
  cameras_{region}.geojson  Flock camera points, split by operator type
  stores_{region}.geojson   home improvement and control retailers
  units.parquet             the full analysis table, queried in-browser by DuckDB-WASM
  chunks.json               RAG passages + metadata
  embeddings.bin            quantised passage vectors (int8)
  tables/*.json             the Phase 4 result tables
  report.md, figures/       the written report and its images

Geometry is simplified with a topology-unaware Douglas-Peucker at ~25 m, which
is far below tract scale and cuts the payload by roughly an order of magnitude.

Run: .venv/bin/python src/analysis/export_web.py
Writes: web/public/data/
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from analysis_common import PROCESSED, PROJECT_ROOT, RAW, REGIONS, TABLES, load_units

WEB_DATA = PROJECT_ROOT / "web" / "public" / "data"
SIMPLIFY_FEET = 80  # ~25 m

KEEP_COLUMNS = [
    "GEOID", "city", "pct_hispanic", "pop_total", "median_hh_income",
    "pop_density_sqkm", "cameras_flock", "cameras_flock_nonretail",
    "cameras_alpr_all", "road_miles", "cameras_per_road_mile",
    "cameras_per_10k_residents", "crime_count", "crime_data_available",
    "retailer_count",
]


def round_coords(obj, places: int = 5):
    """Trim coordinate precision; 5 dp is ~1 m, far finer than tract geometry."""
    if isinstance(obj, float):
        return round(obj, places)
    if isinstance(obj, list):
        return [round_coords(v, places) for v in obj]
    return obj


def export_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    data = json.loads(gdf.to_json())
    for feature in data["features"]:
        feature["geometry"]["coordinates"] = round_coords(
            feature["geometry"]["coordinates"]
        )
        feature.pop("id", None)
    path.write_text(json.dumps(data, separators=(",", ":")))
    print(f"  {path.relative_to(PROJECT_ROOT)} "
          f"({path.stat().st_size / 1e6:.1f} MB, {len(data['features']):,} features)")


def export_tracts(region) -> None:
    units = load_units(region.key, "tract")
    units["geometry"] = units.geometry.simplify(SIMPLIFY_FEET, preserve_topology=True)
    slim = units[[c for c in KEEP_COLUMNS if c in units.columns] + ["geometry"]].copy()

    for col in ("pct_hispanic", "cameras_per_road_mile", "road_miles",
                "cameras_per_10k_residents", "pop_density_sqkm"):
        if col in slim:
            slim[col] = slim[col].round(3)
    slim["crime_data_available"] = slim["crime_data_available"].astype(bool)

    export_geojson(slim.to_crs(4326), WEB_DATA / f"tracts_{region.key}.geojson")


def export_points(region) -> None:
    cams = pd.read_csv(RAW / "osm" / f"alpr_{region.key}.csv")
    cams["operator"] = cams["operator"].fillna("")
    cams["category"] = np.where(
        ~cams["is_flock"], "other ALPR",
        np.where(
            cams["operator"].str.contains(r"home\s*depot|lowe'?s", case=False),
            "Flock (store-operated)", "Flock"),
    )
    cams_gdf = gpd.GeoDataFrame(
        cams[["osm_id", "operator", "manufacturer", "category", "query_date"]],
        geometry=gpd.points_from_xy(cams["lon"], cams["lat"]),
        crs="EPSG:4326",
    )
    export_geojson(cams_gdf, WEB_DATA / f"cameras_{region.key}.geojson")

    stores = pd.read_csv(RAW / "osm" / f"retailers_{region.key}.csv")
    stores["group"] = "home improvement"
    controls = pd.read_csv(RAW / "osm" / f"control_retailers_{region.key}.csv")
    controls["group"] = "control big-box"
    both = pd.concat([stores, controls], ignore_index=True)
    stores_gdf = gpd.GeoDataFrame(
        both[["chain", "name", "group"]],
        geometry=gpd.points_from_xy(both["lon"], both["lat"]),
        crs="EPSG:4326",
    )
    export_geojson(stores_gdf, WEB_DATA / f"stores_{region.key}.geojson")

    labor = pd.read_csv(RAW / "day_labor_sites.csv")
    labor = labor[labor["region"] == region.key]
    verified_path = PROCESSED / "day_labor_sites_verified.csv"
    if verified_path.exists():
        v = pd.read_csv(verified_path)
        labor = v[v["region"] == region.key]
    cols = [c for c in ["name", "address", "site_type", "verification_status"]
            if c in labor.columns]
    labor_gdf = gpd.GeoDataFrame(
        labor[cols],
        geometry=gpd.points_from_xy(labor["lon"], labor["lat"]),
        crs="EPSG:4326",
    )
    export_geojson(labor_gdf, WEB_DATA / f"daylabor_{region.key}.geojson")


def export_tables() -> None:
    out = WEB_DATA / "tables"
    out.mkdir(parents=True, exist_ok=True)
    for csv_path in sorted(TABLES.glob("*.csv")):
        df = pd.read_csv(csv_path)
        target = out / f"{csv_path.stem}.json"
        target.write_text(df.to_json(orient="records"))
        print(f"  {target.relative_to(PROJECT_ROOT)} ({len(df)} rows)")


def export_parquet() -> None:
    import duckdb

    con = duckdb.connect(str(PROCESSED / "flock.duckdb"), read_only=True)
    target = WEB_DATA / "units.parquet"
    con.execute(f"COPY (SELECT * FROM units) TO '{target}' (FORMAT PARQUET)")
    n = con.execute("SELECT count(*) FROM units").fetchone()[0]
    con.close()
    print(f"  {target.relative_to(PROJECT_ROOT)} "
          f"({target.stat().st_size / 1e6:.1f} MB, {n:,} rows)")


def export_rag() -> None:
    """Passages plus int8-quantised embeddings, searchable in the browser."""
    import chromadb
    from chromadb.utils import embedding_functions

    store = PROJECT_ROOT / "rag" / "chroma"
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path=str(store))
    collection = client.get_collection("flock_documents", embedding_function=embedder)
    got = collection.get(include=["documents", "metadatas", "embeddings"])

    vectors = np.asarray(got["embeddings"], dtype=np.float32)
    # Normalise so a dot product is cosine similarity, then quantise to int8.
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    scale = float(np.abs(vectors).max())
    quantised = np.round(vectors / scale * 127).astype(np.int8)

    (WEB_DATA / "embeddings.bin").write_bytes(quantised.tobytes())
    chunks = [
        {"id": cid, "text": doc, **{k: meta[k] for k in
                                    ("file", "title", "publisher", "date", "url", "bucket")}}
        for cid, doc, meta in zip(got["ids"], got["documents"], got["metadatas"])
    ]
    (WEB_DATA / "chunks.json").write_text(json.dumps(chunks, separators=(",", ":")))
    (WEB_DATA / "embeddings_meta.json").write_text(
        json.dumps({"count": len(chunks), "dims": vectors.shape[1],
                    "scale": scale, "dtype": "int8",
                    "model": "Xenova/all-MiniLM-L6-v2"})
    )
    print(f"  {len(chunks):,} chunks, {vectors.shape[1]} dims -> "
          f"chunks.json ({(WEB_DATA / 'chunks.json').stat().st_size / 1e6:.1f} MB), "
          f"embeddings.bin ({(WEB_DATA / 'embeddings.bin').stat().st_size / 1e6:.2f} MB)")


def export_content() -> None:
    for name in ("report.md", "findings.md", "data_sources.md", "manual_downloads.md"):
        src = PROJECT_ROOT / "docs" / name
        if src.exists():
            shutil.copy(src, WEB_DATA / name)
    figures_src = PROJECT_ROOT / "outputs" / "figures"
    figures_dst = PROJECT_ROOT / "web" / "public" / "figures"
    figures_dst.mkdir(parents=True, exist_ok=True)
    for fig in figures_src.glob("*.png"):
        shutil.copy(fig, figures_dst / fig.name)
    shutil.copy(PROJECT_ROOT / "rag" / "documents" / "sources.csv",
                WEB_DATA / "sources.csv")
    print(f"  report + {len(list(figures_dst.glob('*.png')))} figures + sources.csv")


def main() -> int:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    print("Exporting web artifacts")
    for region in REGIONS:
        export_tracts(region)
        export_points(region)
    export_parquet()
    export_tables()
    export_rag()
    export_content()

    total = sum(f.stat().st_size for f in (PROJECT_ROOT / "web" / "public").rglob("*")
                if f.is_file())
    print(f"\nTotal payload: {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
