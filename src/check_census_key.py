"""Verify the Census API key in .env with a small test request.

Run: .venv/bin/python src/check_census_key.py
The key is never printed.
"""

import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_YEARS = [2024, 2023]

# Los Angeles County, CA (06/037) and King County, WA (53/033)
TEST_COUNTIES = [("06", "037"), ("53", "033")]


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("CENSUS_API_KEY", "")

    if not key:
        print("FAIL: CENSUS_API_KEY is empty or missing in .env")
        return 1
    if key != key.strip():
        print("FAIL: CENSUS_API_KEY has leading or trailing whitespace")
        return 1
    if key.startswith(("'", '"')):
        print("FAIL: CENSUS_API_KEY is wrapped in quotes; remove them")
        return 1
    print(f"Key found in .env: {len(key)} characters")

    for year in CANDIDATE_YEARS:
        url = f"https://api.census.gov/data/{year}/acs/acs5"
        rows = []
        for state, county in TEST_COUNTIES:
            params = {
                "get": "NAME,B03002_001E,B03002_012E",
                "for": f"county:{county}",
                "in": f"state:{state}",
                "key": key,
            }
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                body = resp.text.strip()[:200].replace(key, "<KEY>")
                print(f"{year}: HTTP {resp.status_code} - {body}")
                rows = []
                break
            rows.append(resp.json()[1])

        if rows:
            print(f"\nSUCCESS: key works against ACS 5-year {year}")
            print(f"Latest ACS 5-year vintage available: {year}")
            for name, total, hispanic, *_ in rows:
                total_i, hisp_i = int(total), int(hispanic)
                pct = 100 * hisp_i / total_i
                print(
                    f"  {name}: total population {total_i:,}, "
                    f"Hispanic/Latino {hisp_i:,} ({pct:.1f}%)"
                )
            return 0

    print("\nFAIL: no test request succeeded. Common causes:")
    print("  - key not activated yet (click the link in the Census email)")
    print("  - extra spaces or quotes around the key in .env")
    print("  - wrong variable name (must be CENSUS_API_KEY)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
