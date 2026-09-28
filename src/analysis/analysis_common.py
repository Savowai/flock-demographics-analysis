"""Shared loaders for the Phase 4 analysis scripts."""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from common import PROJECT_ROOT, RAW, REGIONS, REGION_BY_KEY  # noqa: E402,F401

PROCESSED = PROJECT_ROOT / "data" / "processed"
TABLES = PROJECT_ROOT / "outputs" / "tables"

# TIGER LSAD codes for incorporated municipalities; 57 is a CDP
# (census designated place), which is unincorporated county land.
INCORPORATED_LSAD = {"25", "43", "47"}


def load_units(region_key: str, level: str = "tract",
               with_city: bool = True) -> gpd.GeoDataFrame:
    """Analysis units for one region, optionally tagged with their city."""
    region = REGION_BY_KEY[region_key]
    units = gpd.read_file(PROCESSED / f"units_{level}_{region_key}.gpkg")
    units = units.to_crs(region.crs)

    if not with_city:
        return units

    places = gpd.read_file(RAW / "tiger" / f"places_{region_key}.gpkg").to_crs(region.crs)
    places = places[places["LSAD"].isin(INCORPORATED_LSAD)]

    # Assign each unit to the city containing its representative point.
    points = units.copy()
    points["geometry"] = units.representative_point()
    assigned = gpd.sjoin(
        points[["GEOID", "geometry"]],
        places[["NAME", "geometry"]].rename(columns={"NAME": "city"}),
        how="left",
        predicate="within",
    )
    assigned = assigned.drop_duplicates("GEOID").set_index("GEOID")["city"]

    units["city"] = units["GEOID"].map(assigned).fillna("(unincorporated county)")
    return units


def model_frame(region_key: str, level: str = "tract") -> pd.DataFrame:
    """Units with model variables prepared and unusable rows dropped."""
    units = load_units(region_key, level)
    df = pd.DataFrame(units.drop(columns="geometry"))

    df["log_road_miles"] = np.log(df["road_miles"].clip(lower=0.01))
    df["log_pop"] = np.log(df["pop_total"].clip(lower=1))
    df["income_10k"] = df["median_hh_income"] / 1e4
    df["pct_hispanic_10"] = df["pct_hispanic"] / 10  # per 10-point change
    df["pop_density_1k"] = df["pop_density_sqkm"] / 1e3
    df["crime_per_1k"] = df["crime_per_1k_residents"]

    before = len(df)
    # A unit with no population, no arterial road and no cameras carries no
    # information about placement; keep anything with any of the three.
    df = df[
        (df["pop_total"] > 0)
        & df["pct_hispanic"].notna()
        & (df["road_miles"] > 0)
    ].copy()
    df["dropped_from"] = before
    return df


def fmt_p(p: float) -> str:
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def save_table(df: pd.DataFrame, name: str) -> Path:
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / name
    df.to_csv(path, index=False)
    print(f"  saved {path.relative_to(PROJECT_ROOT)} ({len(df):,} rows)")
    return path
