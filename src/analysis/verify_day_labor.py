"""Documentary verification of day-labor candidate sites.

What this does and does not do
------------------------------
It CANNOT confirm a hiring site is active. That needs someone physically
present. Informal corners appear and disappear, and a published list is a
record of the past, not the present.

What it CAN do is check that the thing each candidate names actually exists
where the source says it does. NDLON entries are named after a business
("Alhambra Home Depot Location", "Burbank U-Haul Location"), so if that
business is in OpenStreetMap within 200 m of the coordinates, the record is
internally consistent and independently corroborated. If the named business is
nowhere near, the record is stale or misplaced.

Resulting `verification_status`:
  corroborated-business  named business found in OSM near the coordinates
  corroborated-official  formal center listed by a government/organisation source
  unconfirmed            named business not found nearby; needs field checking

`verified` is set to "documented" for corroborated rows - deliberately NOT
"yes", which is reserved for sites confirmed in person.

Raw data is left untouched; output goes to data/processed/.

Run: .venv/bin/python src/analysis/verify_day_labor.py
Writes: data/processed/day_labor_sites_verified.csv
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pandas as pd

from analysis_common import PROCESSED, RAW

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from common import overpass, stamp  # noqa: E402

SEARCH_RADIUS_M = 200

# Business keywords that appear in NDLON site names, mapped to a regex that
# should match the OSM name/brand of the same business.
BUSINESS_PATTERNS = {
    "home depot": r"home\s*depot",
    "u-haul": r"u-?haul",
    "uhaul": r"u-?haul",
    "dunn-edwards": r"dunn[- ]?edwards",
    "shilpark": r"shilpark|paint",
    "paint store": r"paint|dunn|sherwin|behr",
    "7-11": r"7[- ]?eleven|7[- ]?11",
    "7-eleven": r"7[- ]?eleven|7[- ]?11",
    "lowe's": r"lowe'?s",
    "lowes": r"lowe'?s",
    "supermarket": r"market|supermercado|ranch|grocer",
    "market": r"market|supermercado|grocer",
    "gasoline": r"shell|chevron|arco|mobil|76|gas|usa",
    "gas station": r"shell|chevron|arco|mobil|76|gas",
    "shopping center": r"cent(er|re)|plaza|mall",
    "construction warehouse": r"construction|warehouse|builder|lumber",
    "nursery": r"nursery|garden",
    "car wash": r"car\s*wash",
}

QUERY_TEMPLATE = """
[out:json][timeout:180];
nwr(around:{radius},{lat},{lon})["name"];
out center tags;
"""


def expected_pattern(name: str) -> str | None:
    low = (name or "").lower()
    for key, pattern in BUSINESS_PATTERNS.items():
        if key in low:
            return pattern
    return None


def is_formal(site_type: str) -> bool:
    """True only for formal centers.

    Note the substring trap: "informal corner (NDLON map)" CONTAINS "formal".
    """
    return str(site_type).strip().lower().startswith("formal")


def nearby_names(lat: float, lon: float) -> list[str]:
    query = QUERY_TEMPLATE.format(radius=SEARCH_RADIUS_M, lat=lat, lon=lon)
    payload = overpass(query, (0, 0, 0, 0))  # bbox unused by an around: query
    names = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        names.extend(
            str(tags.get(k, "")) for k in ("name", "brand", "operator") if tags.get(k)
        )
    return names


def main() -> int:
    df = pd.read_csv(RAW / "day_labor_sites.csv")
    print(f"Checking {len(df)} candidate sites against OpenStreetMap\n")

    statuses, evidence = [], []
    for i, row in df.iterrows():
        label = f"[{i + 1}/{len(df)}] {str(row['name'])[:48]:50s}"

        if is_formal(row["site_type"]):
            statuses.append("corroborated-official")
            evidence.append("listed by government or operating organisation")
            print(f"  {label} official listing")
            continue

        pattern = expected_pattern(row["name"])
        if pattern is None:
            statuses.append("unconfirmed")
            evidence.append("site name does not identify a checkable business")
            print(f"  {label} no checkable name")
            continue

        try:
            names = nearby_names(row["lat"], row["lon"])
        except Exception as exc:
            statuses.append("unconfirmed")
            evidence.append(f"lookup failed: {type(exc).__name__}")
            print(f"  {label} lookup failed")
            continue

        match = next((n for n in names if re.search(pattern, n, re.IGNORECASE)), None)
        if match:
            statuses.append("corroborated-business")
            evidence.append(f"OSM feature '{match}' within {SEARCH_RADIUS_M} m")
            print(f"  {label} found '{match[:40]}'")
        else:
            statuses.append("unconfirmed")
            evidence.append(
                f"no matching business within {SEARCH_RADIUS_M} m "
                f"({len(names)} named features nearby)"
            )
            print(f"  {label} NOT FOUND")
        time.sleep(1)  # be polite to Overpass

    out = df.copy()
    out["verification_status"] = statuses
    out["verification_evidence"] = evidence
    out["verification_date"] = stamp()
    out["verified"] = out["verification_status"].map(
        lambda s: "documented" if s.startswith("corroborated") else "no"
    )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "day_labor_sites_verified.csv"
    out.to_csv(path, index=False)

    print("\nSummary:")
    print(out.groupby(["region", "verification_status"]).size().to_string())
    print(f"\n{int((out['verified'] == 'documented').sum())} of {len(out)} documented")
    print(
        "NOTE: 'documented' means the named business exists at the coordinates, "
        "NOT that day labor happens there today."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
