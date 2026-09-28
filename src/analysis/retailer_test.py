"""Phase 4.5: the retailer test.

For every Home Depot and Lowe's, record whether a Flock camera sits within
150 m, and whether the store is a verified day-labor site. Then compare camera
presence between day-labor and non-day-labor stores.

Two distinctions matter and are kept separate throughout:

1. Retail-operated cameras (operator = The Home Depot / Lowe's) are the
   store's own private cameras. A store having its own camera says nothing
   about government placement.
2. Non-retail cameras near a store are the interesting case: someone other
   than the chain put a reader next to a hiring site.

The day-labor comparison only runs where enough VERIFIED sites exist. Sites
are verified by hand (`verified` column in data/raw/day_labor_sites.csv); the
test reports that it cannot run rather than substituting unverified candidates.

Run: .venv/bin/python src/analysis/retailer_test.py
Writes: outputs/tables/retailer_camera_proximity.csv
        outputs/tables/retailer_daylabor_comparison.csv
"""

from __future__ import annotations

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats
from shapely.geometry import Point

from analysis_common import PROCESSED, RAW, REGIONS, fmt_p, save_table

RADIUS_M = 150
FEET_PER_M = 3.28084  # both study CRSs are in US survey feet
MIN_VERIFIED_FOR_TEST = 5


def to_gdf(df: pd.DataFrame, crs: int) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        df.copy(),
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    ).to_crs(crs)


def main() -> int:
    per_store, comparisons = [], []

    for region in REGIONS:
        radius_ft = RADIUS_M * FEET_PER_M
        stores = to_gdf(
            pd.read_csv(RAW / "osm" / f"retailers_{region.key}.csv"), region.crs
        )
        cams = pd.read_csv(RAW / "osm" / f"alpr_{region.key}.csv")
        cams["operator"] = cams["operator"].fillna("")
        cams = to_gdf(cams, region.crs)

        flock = cams[cams["is_flock"]]
        retail_op = flock[
            flock["operator"].str.contains(r"home\s*depot|lowe'?s", case=False)
        ]
        nonretail = flock[~flock.index.isin(retail_op.index)]

        # Prefer the verified file if verify_day_labor.py has been run.
        # "yes" = confirmed in person; "documented" = the named business exists
        # at those coordinates (see src/analysis/verify_day_labor.py).
        verified_path = PROCESSED / "day_labor_sites_verified.csv"
        labor_all = pd.read_csv(
            verified_path if verified_path.exists() else RAW / "day_labor_sites.csv"
        )
        labor = labor_all[labor_all["region"] == region.key]
        verified = labor[
            labor["verified"].astype(str).str.lower().isin({"yes", "documented"})
        ]
        tier = (
            "field-verified"
            if (labor["verified"].astype(str).str.lower() == "yes").any()
            else "documented (business confirmed at location, not field-verified)"
        )
        labor_gdf = to_gdf(labor, region.crs) if len(labor) else None
        verified_gdf = to_gdf(verified, region.crs) if len(verified) else None

        rows = []
        for _, store in stores.iterrows():
            buf = store.geometry.buffer(radius_ft)
            near_any = int(flock.within(buf).sum())
            near_retail = int(retail_op.within(buf).sum())
            near_nonretail = int(nonretail.within(buf).sum())

            def nearest(gdf):
                if gdf is None or gdf.empty:
                    return np.nan
                return float(gdf.distance(store.geometry).min() / FEET_PER_M)

            rows.append(
                {
                    "region": region.label,
                    "chain": store["chain"],
                    "name": store.get("name"),
                    "address": store.get("addr"),
                    "lat": store["lat"],
                    "lon": store["lon"],
                    "flock_within_150m": near_any > 0,
                    "flock_cameras_within_150m": near_any,
                    "retail_operated_within_150m": near_retail,
                    "nonretail_flock_within_150m": near_nonretail,
                    "nearest_flock_m": round(nearest(flock), 1),
                    "nearest_nonretail_flock_m": round(nearest(nonretail), 1),
                    "nearest_daylabor_candidate_m": round(nearest(labor_gdf), 1),
                    "nearest_verified_daylabor_m": round(nearest(verified_gdf), 1),
                    "verified_daylabor_within_150m": (
                        bool(verified_gdf.within(buf).any())
                        if verified_gdf is not None
                        else False
                    ),
                }
            )

        store_df = pd.DataFrame(rows)
        store_df["store_group"] = "home improvement (Home Depot / Lowe's)"

        # Control group: big-box retailers that are not day-labor hiring sites.
        controls = to_gdf(
            pd.read_csv(RAW / "osm" / f"control_retailers_{region.key}.csv"),
            region.crs,
        )
        control_rows = []
        for _, store in controls.iterrows():
            buf = store.geometry.buffer(radius_ft)
            control_rows.append(
                {
                    "region": region.label,
                    "chain": store["chain"],
                    "name": store.get("name"),
                    "lat": store["lat"],
                    "lon": store["lon"],
                    "store_group": "control big-box",
                    "flock_within_150m": bool(flock.within(buf).any()),
                    "flock_cameras_within_150m": int(flock.within(buf).sum()),
                    "retail_operated_within_150m": 0,
                    "nonretail_flock_within_150m": int(nonretail.within(buf).sum()),
                    "nearest_flock_m": round(
                        float(flock.distance(store.geometry).min() / FEET_PER_M), 1
                    ),
                }
            )
        control_df = pd.DataFrame(control_rows)
        per_store.append(pd.concat([store_df, control_df], ignore_index=True))

        n = len(store_df)
        with_cam = int(store_df["flock_within_150m"].sum())
        with_nonretail = int((store_df["nonretail_flock_within_150m"] > 0).sum())
        print(f"\n{region.label}: {n} stores")
        print(
            f"  {with_cam} ({100 * with_cam / n:.0f}%) have a Flock camera within "
            f"{RADIUS_M} m; {with_nonretail} ({100 * with_nonretail / n:.0f}%) have a "
            f"NON-retail-operated one"
        )
        by_chain = store_df.groupby("chain")["flock_within_150m"].agg(["size", "sum"])
        for chain, r in by_chain.iterrows():
            print(f"    {chain}: {int(r['sum'])} of {int(r['size'])}")

        # --- home improvement vs control big-box ---------------------------
        # Non-retail cameras only: a chain's own cameras would otherwise make
        # Home Depot look surveilled by someone else.
        hi_rate = (store_df["nonretail_flock_within_150m"] > 0).mean()
        ct_rate = (control_df["nonretail_flock_within_150m"] > 0).mean()
        table = np.array(
            [
                [
                    int((store_df["nonretail_flock_within_150m"] > 0).sum()),
                    int((store_df["nonretail_flock_within_150m"] == 0).sum()),
                ],
                [
                    int((control_df["nonretail_flock_within_150m"] > 0).sum()),
                    int((control_df["nonretail_flock_within_150m"] == 0).sum()),
                ],
            ]
        )
        odds_c, p_c = stats.fisher_exact(table)
        detail_c = (
            f"non-retail Flock camera within {RADIUS_M} m: "
            f"{100 * hi_rate:.0f}% of {len(store_df)} home-improvement stores vs "
            f"{100 * ct_rate:.0f}% of {len(control_df)} control big-box stores"
        )
        print(f"  vs control big-box: {detail_c} "
              f"(odds ratio {odds_c:.2f}, Fisher p={fmt_p(p_c)})")
        comparisons.append(
            {
                "region": region.label,
                "test": "non-retail camera near home-improvement vs control big-box",
                "status": "run",
                "camera_rate_home_improvement": round(hi_rate, 3),
                "camera_rate_control": round(ct_rate, 3),
                "n_home_improvement": len(store_df),
                "n_control": len(control_df),
                "odds_ratio": round(float(odds_c), 3),
                "p_value": float(p_c),
                "detail": detail_c,
            }
        )

        # --- day-labor comparison -----------------------------------------
        n_verified = len(verified)
        if n_verified < MIN_VERIFIED_FOR_TEST:
            msg = (
                f"NOT RUN: only {n_verified} verified day-labor sites in "
                f"{region.label} (need {MIN_VERIFIED_FOR_TEST}). "
                f"{len(labor)} unverified candidates exist; verify them in "
                f"data/raw/day_labor_sites.csv to enable this test."
            )
            print(f"  day-labor comparison: {msg}")
            comparisons.append(
                {
                    "region": region.label,
                    "test": "camera presence: day-labor vs other stores",
                    "status": "not run",
                    "verified_sites_available": n_verified,
                    "detail": msg,
                }
            )
            continue

        grp = store_df.groupby("verified_daylabor_within_150m")["flock_within_150m"]
        table = pd.crosstab(
            store_df["verified_daylabor_within_150m"], store_df["flock_within_150m"]
        )
        odds, p = stats.fisher_exact(table) if table.shape == (2, 2) else (np.nan, np.nan)
        rates = grp.mean().to_dict()
        detail = (
            f"stores at verified day-labor sites: "
            f"{100 * rates.get(True, float('nan')):.0f}% have a camera; "
            f"other stores: {100 * rates.get(False, float('nan')):.0f}%"
        )
        print(f"  day-labor comparison: {detail} (Fisher p={fmt_p(p)})")
        comparisons.append(
            {
                "region": region.label,
                "test": "camera presence: day-labor vs other stores",
                "status": "run",
                "verified_sites_available": n_verified,
                "verification_tier": tier,
                "stores_at_daylabor_sites": int(
                    store_df["verified_daylabor_within_150m"].sum()
                ),
                "camera_rate_daylabor": round(rates.get(True, np.nan), 3),
                "camera_rate_other": round(rates.get(False, np.nan), 3),
                "odds_ratio": round(odds, 3) if odds == odds else np.nan,
                "p_value": p,
                "detail": detail,
            }
        )

    save_table(pd.concat(per_store, ignore_index=True),
               "retailer_camera_proximity.csv")
    save_table(pd.DataFrame(comparisons), "retailer_daylabor_comparison.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
