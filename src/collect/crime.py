"""Reported crime from the LAPD and Seattle open data portals.

IMPORTANT LIMITATION: these are city police departments, not county-wide.
LAPD covers the City of Los Angeles (~3.8M of LA County's 9.8M residents);
SPD covers the City of Seattle (~750k of King County's 2.3M). Tracts outside
those city limits have no crime data at all - they are not zero-crime tracts.
Phase 3 marks them as missing, and Phase 4 models them separately rather than
treating missing as zero.

Both departments now publish NIBRS-coded offences, so the two cities use the
same crime taxonomy and are directly comparable.

Run: .venv/bin/python src/collect/crime.py
Writes: data/raw/crime/crime_{region}.csv
"""

from __future__ import annotations

import sys

import pandas as pd

from common import RAW, session, stamp

START_DATE = "2025-01-01"  # recent window, aligned with 2026 camera data

SOURCES = {
    "la": {
        "portal": "data.lacity.org",
        "dataset": "k7nn-b2ep",
        "title": "LAPD NIBRS Offenses Dataset",
        "date_field": "date_occ",
        "lat": "hndrdth_lat",
        "lon": "hndrdth_lon",
        "select": [
            "caseno", "date_occ", "nibr_code", "nibr_description",
            "crime_against", "area_name", "hndrdth_lat", "hndrdth_lon",
        ],
    },
    "king": {
        "portal": "data.seattle.gov",
        "dataset": "tazs-3rd5",
        "title": "SPD Crime Data: 2008-Present",
        "date_field": "offense_date",
        "lat": "latitude",
        "lon": "longitude",
        "select": [
            "report_number", "offense_date", "nibrs_offense_code",
            "nibrs_offense_code_description", "nibrs_crime_against_category",
            "offense_category", "neighborhood", "latitude", "longitude",
        ],
    },
}

PAGE = 50_000


def fetch(cfg: dict) -> pd.DataFrame:
    url = f"https://{cfg['portal']}/resource/{cfg['dataset']}.json"
    where = (
        f"{cfg['date_field']} >= '{START_DATE}' "
        f"AND {cfg['lat']} IS NOT NULL AND {cfg['lon']} IS NOT NULL"
    )
    frames, offset = [], 0
    with session() as s:
        while True:
            params = {
                "$select": ",".join(cfg["select"]),
                "$where": where,
                "$order": f"{cfg['date_field']}",
                "$limit": PAGE,
                "$offset": offset,
            }
            resp = s.get(url, params=params, timeout=300)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            frames.append(pd.DataFrame(batch))
            offset += PAGE
            print(f"    {offset:,} rows requested...", end="\r")
            if len(batch) < PAGE:
                break
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    outdir = RAW / "crime"
    outdir.mkdir(parents=True, exist_ok=True)
    today = stamp()

    for key, cfg in SOURCES.items():
        print(f"{cfg['title']} ({cfg['portal']})")
        df = fetch(cfg)
        if df.empty:
            print("  WARNING: no rows returned")
            continue

        df = df.rename(columns={cfg["lat"]: "lat", cfg["lon"]: "lon",
                                cfg["date_field"]: "date_occurred"})
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

        before = len(df)
        # Drop 0,0 placeholder coordinates used for redacted locations
        df = df[(df["lat"].abs() > 0.01) & (df["lon"].abs() > 0.01)].dropna(
            subset=["lat", "lon"]
        )
        df["region"] = key
        df["source_dataset"] = f"{cfg['portal']}/{cfg['dataset']}"
        df["retrieved"] = today

        out = outdir / f"crime_{key}.csv"
        df.to_csv(out, index=False)
        span = f"{df['date_occurred'].min()[:10]} to {df['date_occurred'].max()[:10]}"
        print(
            f"\n  {before:,} rows, {len(df):,} with usable coordinates "
            f"({before - len(df):,} dropped), {span} -> {out.name}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
