"""Phase 3: clean everything and join it onto tracts and block groups.

Produces one analysis row per geographic unit per region, with the camera
counts, demographics and controls the Phase 4 models need.

Design decisions worth knowing about:

* Everything is reprojected to the region's projected CRS (EPSG:2229 for LA,
  EPSG:2285 for King) before any distance or length calculation. Lengths in
  those systems are US survey feet, converted to miles here.
* Cameras are counted three ways: all ALPR, all Flock, and Flock excluding
  cameras whose operator is a retail chain. Store-owned cameras are private
  placements, not government ones, and pooling them would answer the wrong
  question.
* Crime is only joined for units inside the reporting city (LAPD = City of
  Los Angeles, SPD = City of Seattle). Units outside get NULL, never 0,
  and `crime_data_available` records which is which.

Run: .venv/bin/python src/analysis/build_units.py
Writes: data/processed/units_{tract,bg}_{la,king}.gpkg
        data/processed/flock.duckdb  (table `units`, plus point tables)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from common import ACS_YEAR, PROJECT_ROOT, RAW, REGIONS  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
FEET_PER_MILE = 5280.0
SQM_PER_SQKM = 1e6

# Camera operators that are retail chains: privately owned, not government.
PRIVATE_RETAIL_RE = re.compile(r"home\s*depot|lowe'?s", re.IGNORECASE)


def load_points(path: Path, crs: int) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, low_memory=False)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )
    return gdf.to_crs(crs)


def count_in_units(points: gpd.GeoDataFrame, units: gpd.GeoDataFrame,
                   label: str) -> pd.Series:
    """Count points falling inside each unit; returns a Series indexed by GEOID."""
    if points.empty:
        return pd.Series(0, index=units["GEOID"], name=label, dtype="int64")
    joined = gpd.sjoin(points, units[["GEOID", "geometry"]], how="inner",
                       predicate="within")
    counts = joined.groupby("GEOID").size()
    return counts.reindex(units["GEOID"], fill_value=0).rename(label)


def road_miles_per_unit(roads: gpd.GeoDataFrame,
                        units: gpd.GeoDataFrame) -> pd.Series:
    """Split road lines at unit boundaries and sum length inside each unit."""
    pieces = gpd.overlay(
        roads[["geometry"]], units[["GEOID", "geometry"]], how="identity",
        keep_geom_type=True,
    )
    pieces = pieces[pieces["GEOID"].notna()]
    miles = pieces.geometry.length.groupby(pieces["GEOID"]).sum() / FEET_PER_MILE
    return miles.reindex(units["GEOID"], fill_value=0.0).rename("road_miles")


def build(region, level: str) -> gpd.GeoDataFrame:
    crs = region.crs
    print(f"\n{region.label} / {level}")

    units = gpd.read_file(RAW / "tiger" / f"{level}_{region.key}.gpkg").to_crs(crs)
    units = units[["GEOID", "ALAND", "geometry"]].copy()
    units["land_sqkm"] = units["ALAND"] / SQM_PER_SQKM

    # --- demographics -----------------------------------------------------
    acs = pd.read_csv(
        RAW / "acs" / f"acs{ACS_YEAR}_{level}_{region.key}.csv",
        dtype={"GEOID": str},
    )
    units = units.merge(acs.drop(columns=["region"]), on="GEOID", how="left")
    missing_acs = int(units["pop_total"].isna().sum())
    if missing_acs:
        print(f"  WARNING: {missing_acs} units without ACS data")

    units["pct_hispanic"] = np.where(
        units["pop_total_b03002"] > 0,
        100 * units["pop_hispanic"] / units["pop_total_b03002"],
        np.nan,
    )
    units["pop_density_sqkm"] = np.where(
        units["land_sqkm"] > 0, units["pop_total"] / units["land_sqkm"], np.nan
    )

    # --- cameras ----------------------------------------------------------
    cams = load_points(RAW / "osm" / f"alpr_{region.key}.csv", crs)
    cams["operator"] = cams["operator"].fillna("")
    cams["is_private_retail"] = cams["operator"].str.contains(PRIVATE_RETAIL_RE)
    flock = cams[cams["is_flock"]]

    units = units.join(count_in_units(cams, units, "cameras_alpr_all").reset_index(drop=True))
    units = units.join(count_in_units(flock, units, "cameras_flock").reset_index(drop=True))
    units = units.join(
        count_in_units(flock[flock["is_private_retail"]], units,
                       "cameras_flock_retail").reset_index(drop=True)
    )
    units["cameras_flock_nonretail"] = (
        units["cameras_flock"] - units["cameras_flock_retail"]
    )

    # --- roads ------------------------------------------------------------
    roads = gpd.read_file(RAW / "osm" / f"roads_{region.key}.gpkg").to_crs(crs)
    units = units.join(road_miles_per_unit(roads, units).reset_index(drop=True))

    # --- crime, only where the reporting agency polices ---------------------
    city = gpd.read_file(RAW / "tiger" / f"city_{region.key}.gpkg").to_crs(crs)
    city_poly = city.union_all()
    # A unit counts as covered if most of it lies inside the city.
    overlap = units.geometry.intersection(city_poly).area / units.geometry.area
    units["crime_data_available"] = overlap > 0.5

    crime = load_points(RAW / "crime" / f"crime_{region.key}.csv", crs)
    crime_counts = count_in_units(crime, units, "crime_count").reset_index(drop=True)
    units["crime_count"] = np.where(
        units["crime_data_available"], crime_counts, np.nan
    )

    # --- retailers and day-labor sites -------------------------------------
    retail = load_points(RAW / "osm" / f"retailers_{region.key}.csv", crs)
    units = units.join(count_in_units(retail, units, "retailer_count").reset_index(drop=True))

    labor_all = pd.read_csv(RAW / "day_labor_sites.csv")
    labor = labor_all[labor_all["region"] == region.key]
    labor_path = PROCESSED / f"_labor_{region.key}.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    labor.to_csv(labor_path, index=False)
    units = units.join(
        count_in_units(load_points(labor_path, crs), units,
                       "day_labor_candidate_count").reset_index(drop=True)
    )
    labor_path.unlink()

    # --- rates ------------------------------------------------------------
    units["cameras_per_road_mile"] = np.where(
        units["road_miles"] > 0, units["cameras_flock"] / units["road_miles"], np.nan
    )
    units["cameras_per_10k_residents"] = np.where(
        units["pop_total"] > 0, 1e4 * units["cameras_flock"] / units["pop_total"], np.nan
    )
    units["crime_per_1k_residents"] = np.where(
        (units["pop_total"] > 0) & units["crime_data_available"],
        1e3 * units["crime_count"] / units["pop_total"],
        np.nan,
    )

    units["region"] = region.key
    units["region_label"] = region.label
    units["geo_level"] = level
    units["crs_used"] = f"EPSG:{crs}"

    with_cams = int((units["cameras_flock"] > 0).sum())
    print(
        f"  {len(units):,} units | Flock cameras joined: "
        f"{int(units['cameras_flock'].sum()):,} of {len(flock):,} "
        f"({with_cams:,} units have at least one)"
    )
    print(
        f"  road-miles {units['road_miles'].sum():,.0f} | "
        f"crime coverage {int(units['crime_data_available'].sum()):,} units "
        f"({100 * units['crime_data_available'].mean():.0f}%), "
        f"{int(units['crime_count'].sum(skipna=True)):,} offences joined"
    )
    print(
        f"  retailers {int(units['retailer_count'].sum())} | "
        f"day-labor candidates {int(units['day_labor_candidate_count'].sum())}"
    )
    return units


COLUMNS = [
    "GEOID", "region", "region_label", "geo_level", "crs_used", "NAME",
    "acs_year", "pop_total", "pop_hispanic", "pop_nh_white", "pct_hispanic",
    "median_hh_income", "land_sqkm", "pop_density_sqkm",
    "cameras_alpr_all", "cameras_flock", "cameras_flock_retail",
    "cameras_flock_nonretail", "road_miles", "cameras_per_road_mile",
    "cameras_per_10k_residents", "crime_data_available", "crime_count",
    "crime_per_1k_residents", "retailer_count", "day_labor_candidate_count",
]


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    frames = []

    for region in REGIONS:
        for level in ("tract", "bg"):
            units = build(region, level)
            out = PROCESSED / f"units_{level}_{region.key}.gpkg"
            units.to_file(out, driver="GPKG", layer="units")
            frames.append(pd.DataFrame(units[COLUMNS]))

    combined = pd.concat(frames, ignore_index=True)

    db_path = PROCESSED / "flock.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.register("units_df", combined)
    con.execute("CREATE TABLE units AS SELECT * FROM units_df")
    con.unregister("units_df")  # keep the temporary view out of the saved database

    # Point tables, useful for the Phase 7 query interface. The two crime feeds
    # have different schemas (LAPD vs SPD), so union_by_name fills the gaps.
    point_tables = {
        "cameras": [RAW / "osm" / f"alpr_{r.key}.csv" for r in REGIONS],
        "retailers": [RAW / "osm" / f"retailers_{r.key}.csv" for r in REGIONS],
        "crime": [RAW / "crime" / f"crime_{r.key}.csv" for r in REGIONS],
        "day_labor_sites": [RAW / "day_labor_sites.csv"],
    }
    for name, paths in point_tables.items():
        files = ", ".join(f"'{p}'" for p in paths)
        con.execute(
            f"CREATE TABLE {name} AS SELECT * FROM "
            f"read_csv_auto([{files}], union_by_name=true, sample_size=-1)"
        )

    print("\nDuckDB tables:")
    for (name,) in con.execute(
        "SELECT table_name FROM information_schema.tables ORDER BY table_name"
    ).fetchall():
        n = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        print(f"  {name}: {n:,} rows")
    con.close()

    print(f"\nWrote {len(frames)} GeoPackages and {db_path.name} to data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
