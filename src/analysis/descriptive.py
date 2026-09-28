"""Phase 4.1: descriptive comparison of camera rates by percent-Hispanic quartile.

No controls here - this is the raw picture, reported both as a raw count and
normalised by arterial road-miles, which is the fairest simple denominator
(cameras are mounted on roads).

Run: .venv/bin/python src/analysis/descriptive.py
Writes: outputs/tables/descriptive_quartiles.csv
        outputs/tables/descriptive_by_city.csv
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from analysis_common import REGIONS, model_frame, save_table


def quartile_table(df: pd.DataFrame, region_label: str, level: str) -> pd.DataFrame:
    d = df.copy()
    d["quartile"] = pd.qcut(d["pct_hispanic"], 4, labels=[1, 2, 3, 4])

    rows = []
    for q, g in d.groupby("quartile", observed=True):
        rows.append(
            {
                "region": region_label,
                "level": level,
                "quartile": int(q),
                "units": len(g),
                "pct_hispanic_range": f"{g['pct_hispanic'].min():.1f}-{g['pct_hispanic'].max():.1f}",
                "mean_pct_hispanic": round(g["pct_hispanic"].mean(), 1),
                "total_flock_cameras": int(g["cameras_flock"].sum()),
                "mean_cameras_per_unit": round(g["cameras_flock"].mean(), 3),
                "pct_units_with_camera": round(100 * (g["cameras_flock"] > 0).mean(), 1),
                "cameras_per_road_mile": round(
                    g["cameras_flock"].sum() / g["road_miles"].sum(), 4
                ),
                "cameras_per_10k_residents": round(
                    1e4 * g["cameras_flock"].sum() / g["pop_total"].sum(), 2
                ),
                "mean_median_income": round(g["median_hh_income"].mean(), 0),
                "mean_pop_density_sqkm": round(g["pop_density_sqkm"].mean(), 0),
                "mean_road_miles": round(g["road_miles"].mean(), 2),
                # Aggregate rate (total offences / total population) rather than
                # the mean of per-unit rates, which tiny-population downtown
                # tracts distort badly. Covered units only.
                "crime_per_1k_residents": round(
                    1e3
                    * g.loc[g["crime_data_available"], "crime_count"].sum()
                    / max(g.loc[g["crime_data_available"], "pop_total"].sum(), 1),
                    1,
                ),
                "units_with_crime_data": int(g["crime_data_available"].sum()),
            }
        )
    out = pd.DataFrame(rows)

    # Ratio of top to bottom quartile, the headline descriptive number.
    top, bottom = out.iloc[-1], out.iloc[0]
    out["ratio_q4_to_q1_per_road_mile"] = round(
        top["cameras_per_road_mile"] / bottom["cameras_per_road_mile"], 2
    )
    return out


def city_table(df: pd.DataFrame, region_label: str) -> pd.DataFrame:
    g = df.groupby("city")
    out = pd.DataFrame(
        {
            "region": region_label,
            "units": g.size(),
            "population": g["pop_total"].sum(),
            "pct_hispanic": (
                100 * g["pop_hispanic"].sum() / g["pop_total"].sum()
            ).round(1),
            "flock_cameras": g["cameras_flock"].sum().astype(int),
            "flock_cameras_nonretail": g["cameras_flock_nonretail"].sum().astype(int),
            "road_miles": g["road_miles"].sum().round(1),
        }
    ).reset_index()
    out["cameras_per_road_mile"] = (
        out["flock_cameras"] / out["road_miles"]
    ).round(4)
    out["cameras_per_10k_residents"] = (
        1e4 * out["flock_cameras"] / out["population"].clip(lower=1)
    ).round(2)
    out["has_cameras"] = out["flock_cameras"] > 0
    return out.sort_values("flock_cameras", ascending=False)


def main() -> int:
    quartiles, cities = [], []

    for region in REGIONS:
        for level in ("tract", "bg"):
            df = model_frame(region.key, level)
            q = quartile_table(df, region.label, level)
            quartiles.append(q)

            if level == "tract":
                print(f"\n{region.label} - tracts by percent-Hispanic quartile")
                print(
                    q[
                        [
                            "quartile", "units", "pct_hispanic_range",
                            "total_flock_cameras", "mean_cameras_per_unit",
                            "cameras_per_road_mile", "cameras_per_10k_residents",
                            "crime_per_1k_residents", "units_with_crime_data",
                        ]
                    ].to_string(index=False)
                )
                ratio = q["ratio_q4_to_q1_per_road_mile"].iloc[0]
                direction = "more" if ratio > 1 else "fewer"
                print(
                    f"  Most-Hispanic quartile has {ratio}x {direction} cameras "
                    f"per road-mile than the least-Hispanic quartile."
                )

                c = city_table(df, region.label)
                cities.append(c)
                with_cams = int(c["has_cameras"].sum())
                print(
                    f"  Cities/areas: {len(c)}, {with_cams} with at least one "
                    f"mapped Flock camera"
                )
                print("  Top 8 by camera count:")
                print(
                    c.head(8)[
                        ["city", "pct_hispanic", "flock_cameras",
                         "cameras_per_road_mile", "population"]
                    ].to_string(index=False)
                )

    save_table(pd.concat(quartiles, ignore_index=True), "descriptive_quartiles.csv")
    save_table(pd.concat(cities, ignore_index=True), "descriptive_by_city.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
