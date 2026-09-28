"""Phase 4.2b: city-level adoption.

Flock is bought city by city, so "which neighbourhoods have cameras" and
"which cities bought cameras" are different questions with different meanings.
This script asks the second one: does a city's Hispanic share predict whether
it has Flock cameras at all, and how many?

Two models per region, one row per incorporated city:
  A. Logistic     P(city has any non-retail Flock camera)
  B. Neg. binomial  camera count, offset by arterial road-miles

Caveats that limit how far this can be pushed:
  - A camera inside a city's limits was not necessarily bought by that city.
    County sheriffs, transit agencies, HOAs and businesses also deploy them.
    Retail-chain cameras are excluded, but other private cameras remain.
  - Sample sizes are small (88 LA cities, 38 King) - fine for a broad pattern,
    not for fine-grained control.
  - Absence of a mapped camera is not proof a city has none; see the
    crowdsourcing limitation in docs/data_sources.md.

Run: .venv/bin/python src/analysis/city_adoption.py
Writes: outputs/tables/city_adoption_models.csv
        outputs/tables/city_profiles.csv
"""

from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from analysis_common import REGIONS, fmt_p, model_frame, save_table

warnings.filterwarnings("ignore")

TERMS = ["pct_hispanic_10", "log_pop", "income_10k", "pop_density_1k"]


def city_frame(region_key: str) -> pd.DataFrame:
    df = model_frame(region_key, "tract")
    df = df[df["city"] != "(unincorporated county)"]

    g = df.groupby("city")
    cities = pd.DataFrame(
        {
            "tracts": g.size(),
            "pop_total": g["pop_total"].sum(),
            "pop_hispanic": g["pop_hispanic"].sum(),
            "road_miles": g["road_miles"].sum(),
            "cameras_flock": g["cameras_flock"].sum(),
            "cameras_flock_nonretail": g["cameras_flock_nonretail"].sum(),
            "land_sqkm": g["land_sqkm"].sum(),
            # Population-weighted median income across the city's tracts
            "median_hh_income": g.apply(
                lambda x: np.average(
                    x["median_hh_income"].fillna(x["median_hh_income"].median()),
                    weights=x["pop_total"].clip(lower=1),
                ),
                include_groups=False,
            ),
        }
    ).reset_index()

    cities["pct_hispanic"] = 100 * cities["pop_hispanic"] / cities["pop_total"]
    cities["pct_hispanic_10"] = cities["pct_hispanic"] / 10
    cities["log_pop"] = np.log(cities["pop_total"].clip(lower=1))
    cities["income_10k"] = cities["median_hh_income"] / 1e4
    cities["pop_density_1k"] = cities["pop_total"] / cities["land_sqkm"] / 1e3
    cities["log_road_miles"] = np.log(cities["road_miles"].clip(lower=0.01))
    cities["has_cameras"] = (cities["cameras_flock_nonretail"] > 0).astype(int)
    cities["cameras_per_road_mile"] = (
        cities["cameras_flock_nonretail"] / cities["road_miles"]
    )
    return cities


rows: list[dict] = []


def record(region_label, model, term, beta, se, p, n, effect_label, effect):
    rows.append(
        {
            "region": region_label,
            "model": model,
            "term": term,
            "coefficient": round(beta, 4),
            "std_error": round(se, 4),
            effect_label: round(effect, 4),
            "ci_low": round(np.exp(beta - 1.96 * se), 4),
            "ci_high": round(np.exp(beta + 1.96 * se), 4),
            "p_value": p,
            "significant_05": p < 0.05,
            "n_cities": n,
        }
    )


def main() -> int:
    profiles = []

    for region in REGIONS:
        cities = city_frame(region.key)
        profiles.append(cities.assign(region=region.label))

        adopters = int(cities["has_cameras"].sum())
        print(f"\n{region.label}: {len(cities)} incorporated cities, "
              f"{adopters} with mapped non-retail Flock cameras")

        adopt = cities.groupby("has_cameras")["pct_hispanic"].agg(["count", "mean"])
        for has, row in adopt.iterrows():
            label = "with cameras" if has else "without cameras"
            print(f"  cities {label:16s}: n={int(row['count']):>3}, "
                  f"mean Hispanic share {row['mean']:.1f}%")

        X = sm.add_constant(cities[TERMS].astype(float))

        # A. Does a city have any cameras at all?
        logit = sm.Logit(cities["has_cameras"], X).fit(disp=False)
        b, se, p = (
            logit.params["pct_hispanic_10"],
            logit.bse["pct_hispanic_10"],
            logit.pvalues["pct_hispanic_10"],
        )
        record(region.label, "A. logistic: any cameras", "pct_hispanic_10",
               b, se, p, len(cities), "odds_ratio", np.exp(b))
        print(f"  A. odds of having cameras: x{np.exp(b):.2f} per +10pt "
              f"Hispanic (p={fmt_p(p)})")

        # B. How many, given road mileage?
        y = cities["cameras_flock_nonretail"].astype(float)
        offset = cities["log_road_miles"].values
        pois = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
        mu = pois.mu
        aux = sm.OLS(((y - mu) ** 2 - y) / mu, mu).fit()
        alpha = float(np.clip(aux.params.iloc[0], 1e-6, None))
        nb = sm.GLM(
            y, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset
        ).fit(cov_type="HC1")
        b, se, p = (
            nb.params["pct_hispanic_10"],
            nb.bse["pct_hispanic_10"],
            nb.pvalues["pct_hispanic_10"],
        )
        record(region.label, "B. negative binomial: camera count",
               "pct_hispanic_10", b, se, p, len(cities), "rate_ratio", np.exp(b))
        print(f"  B. camera count per road-mile: x{np.exp(b):.2f} per +10pt "
              f"Hispanic (p={fmt_p(p)})")

        top = cities.nlargest(6, "cameras_per_road_mile")[
            ["city", "pct_hispanic", "cameras_flock_nonretail",
             "cameras_per_road_mile", "pop_total"]
        ]
        print("  Highest camera density:")
        print(top.round(3).to_string(index=False))

    save_table(pd.DataFrame(rows), "city_adoption_models.csv")
    save_table(pd.concat(profiles, ignore_index=True), "city_profiles.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
