"""Shared configuration and helpers for the collection scripts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw"

# ACS 5-year vintage verified as the latest available (see src/check_census_key.py)
ACS_YEAR = 2024
TIGER_YEAR = 2024

USER_AGENT = (
    "flock-demographics-analysis/0.1 (academic research; contact via GitHub issues)"
)


@dataclass(frozen=True)
class Region:
    key: str            # short name used in filenames
    label: str
    state_fips: str
    county_fips: str
    crs: int            # projected CRS for distance/length work
    # bbox as (south, west, north, east) - Overpass order
    bbox: tuple[float, float, float, float]
    tags: dict = field(default_factory=dict)

    @property
    def geoid_county(self) -> str:
        return self.state_fips + self.county_fips


REGIONS = [
    Region(
        key="la",
        label="Los Angeles County, CA",
        state_fips="06",
        county_fips="037",
        crs=2229,  # NAD83 / California zone 5 (ftUS)
        bbox=(33.20, -118.95, 34.84, -117.64),
    ),
    Region(
        key="king",
        label="King County, WA",
        state_fips="53",
        county_fips="033",
        crs=2285,  # NAD83 / Washington North (ftUS)
        bbox=(47.07, -122.55, 47.80, -121.06),
    ),
]

REGION_BY_KEY = {r.key: r for r in REGIONS}


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 300) -> Path:
    """Download url to dest unless it already exists. Returns dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        print(f"  cached: {dest.relative_to(PROJECT_ROOT)} "
              f"({dest.stat().st_size / 1e6:.1f} MB)")
        return dest

    print(f"  GET {url}")
    with session() as s:
        for attempt in range(3):
            try:
                with s.get(url, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with open(tmp, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            fh.write(chunk)
                    tmp.replace(dest)
                break
            except requests.RequestException as exc:
                if attempt == 2:
                    raise
                print(f"  retry {attempt + 1}/2 after error: {exc}")
                time.sleep(5 * (attempt + 1))

    print(f"  saved: {dest.relative_to(PROJECT_ROOT)} "
          f"({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def overpass(query_template: str, bbox: tuple[float, float, float, float]) -> dict:
    """Run an Overpass query. `{bbox}` in the template is filled with south,west,north,east.

    Tries each endpoint up to 3 times; Overpass returns 504 under load often
    enough that retrying is normal rather than exceptional.
    """
    query = query_template.format(bbox=",".join(str(v) for v in bbox))
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(3):
            try:
                with session() as s:
                    resp = s.post(endpoint, data={"data": query}, timeout=600)
                if resp.status_code == 200:
                    return resp.json()
                last_error = f"HTTP {resp.status_code} from {endpoint}"
            except Exception as exc:  # network / decode errors
                last_error = f"{type(exc).__name__}: {exc}"
            print(f"  {last_error}; retrying")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Overpass failed: {last_error}")


def stamp() -> str:
    """UTC date for provenance records."""
    return time.strftime("%Y-%m-%d", time.gmtime())
