"""ACS 5-year estimates for LA County and King County, at tract and block-group level.

Pulls:
  B03002 (Hispanic or Latino origin by race) - total, Hispanic/Latino, non-Hispanic white
  B01003_001E total population
  B19013_001E median household income
Land area comes from the TIGER/Line files (ALAND), joined in Phase 3.

Run: .venv/bin/python src/collect/census_acs.py
Writes: data/raw/acs/acs{YEAR}_{tract|bg}_{region}.csv
"""

from __future__ import annotations

import os
import sys

import pandas as pd
from dotenv import load_dotenv

from common import ACS_YEAR, PROJECT_ROOT, RAW, REGIONS, session, stamp

VARIABLES = {
    "B03002_001E": "pop_total_b03002",
    "B03002_012E": "pop_hispanic",
    "B03002_003E": "pop_nh_white",
    "B01003_001E": "pop_total",
    "B19013_001E": "median_hh_income",
}

BASE = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"


def fetch(level: str, region, key: str) -> pd.DataFrame:
    if level == "tract":
        geo_for = "tract:*"
        geo_in = f"state:{region.state_fips} county:{region.county_fips}"
    elif level == "bg":
        geo_for = "block group:*"
        geo_in = f"state:{region.state_fips} county:{region.county_fips} tract:*"
    else:
        raise ValueError(level)

    params = {
        "get": "NAME," + ",".join(VARIABLES),
        "for": geo_for,
        "in": geo_in,
        "key": key,
    }
    with session() as s:
        resp = s.get(BASE, params=params, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(
            f"{level}/{region.key}: HTTP {resp.status_code} "
            f"{resp.text.strip()[:200].replace(key, '<KEY>')}"
        )

    rows = resp.json()
    df = pd.DataFrame(rows[1:], columns=rows[0]).rename(columns=VARIABLES)

    geo_cols = ["state", "county", "tract"] + (["block group"] if level == "bg" else [])
    df["GEOID"] = df[geo_cols].agg("".join, axis=1)

    for col in VARIABLES.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
        # Census uses large negative sentinels for missing/suppressed values
        df.loc[df[col] < -1e6, col] = pd.NA

    df["region"] = region.key
    df["acs_year"] = ACS_YEAR
    df["retrieved"] = stamp()
    keep = ["GEOID", "NAME", "region", "acs_year", "retrieved"] + list(VARIABLES.values())
    return df[keep].sort_values("GEOID").reset_index(drop=True)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("CENSUS_API_KEY", "").strip()
    if not key:
        print("CENSUS_API_KEY missing from .env")
        return 1

    outdir = RAW / "acs"
    outdir.mkdir(parents=True, exist_ok=True)

    for region in REGIONS:
        for level in ("tract", "bg"):
            df = fetch(level, region, key)
            path = outdir / f"acs{ACS_YEAR}_{level}_{region.key}.csv"
            df.to_csv(path, index=False)

            pop = df["pop_total"].sum()
            hisp = df["pop_hispanic"].sum()
            zero_pop = int((df["pop_total"] == 0).sum())
            no_income = int(df["median_hh_income"].isna().sum())
            print(
                f"{region.label} {level}: {len(df):,} units, "
                f"pop {pop:,.0f}, Hispanic/Latino {100 * hisp / pop:.1f}%, "
                f"{zero_pop} zero-population units, "
                f"{no_income} without median income -> {path.name}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
