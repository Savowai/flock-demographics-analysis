"""Phase 4.2-4.4: negative binomial models, spatial checks, robustness.

Outcome: number of Flock cameras in a unit (a count, overdispersed - many
zeros, a few units with many cameras - hence negative binomial rather than
Poisson).

Exposure: arterial road-miles enter as an offset, i.e. the model predicts
cameras PER ROAD-MILE. A tract with twice the arterial mileage is expected to
have twice the cameras before any demographic effect is considered.

Main variable: percent Hispanic/Latino, scaled per 10 percentage points, so a
coefficient reads as "each 10-point increase in Hispanic share multiplies the
expected camera count by exp(beta)".

Models per region:
  M1 base         cameras ~ pct_hispanic + log_pop + income + density
  M2 + crime      same, restricted to units with crime data
  M3 within-city  M1 plus city fixed effects, so comparisons happen between
                  neighbourhoods policed by the same agency
  M4 block group  M1 refitted at block-group level (robustness)

Retail-operated cameras (Home Depot, Lowe's) are excluded from the outcome in
the main specification: they are private placements, not government ones.

Spatial checks: Moran's I on M1 residuals, and if significant, a spatial lag
model on log(cameras + 1) for comparison. Spatial lag is fitted on a
transformed continuous outcome because a spatial-lag negative binomial is not
available in spreg; it is a cross-check on direction and significance, not a
replacement for the count model.

Run: .venv/bin/python src/analysis/models.py
Writes: outputs/tables/model_coefficients.csv
        outputs/tables/model_summary.csv
        outputs/tables/spatial_diagnostics.csv
"""

from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda.moran import Moran
from libpysal.weights import Queen
from spreg import GM_Lag

from analysis_common import REGIONS, fmt_p, load_units, model_frame, save_table

warnings.filterwarnings("ignore")

OUTCOME = "cameras_flock_nonretail"
BASE_TERMS = ["pct_hispanic_10", "log_pop", "income_10k", "pop_density_1k"]

coef_rows: list[dict] = []
summary_rows: list[dict] = []
spatial_rows: list[dict] = []


def fit_nb(df: pd.DataFrame, terms: list[str], label: str, region_label: str,
           level: str, note: str = "") -> tuple:
    """Fit a negative binomial with log(road_miles) as offset."""
    d = df.dropna(subset=terms + [OUTCOME, "log_road_miles"]).copy()
    X = sm.add_constant(d[terms].astype(float), has_constant="add")
    y = d[OUTCOME].astype(float)

    offset = d["log_road_miles"].values

    # Full negative binomial MLE fails to converge on alpha for these data
    # (the Hessian is not invertible at the optimum), so alpha is estimated in
    # the standard two-step way: fit Poisson, then regress the scaled squared
    # residuals on the fitted mean (Cameron & Trivedi). The count model is then
    # a GLM with that alpha held fixed, with heteroskedasticity-robust standard
    # errors since alpha is estimated rather than known.
    pois = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
    mu = pois.mu
    aux = sm.OLS(((y - mu) ** 2 - y) / mu, mu).fit()
    alpha = float(np.clip(aux.params.iloc[0], 1e-6, None))

    res = sm.GLM(
        y, X, family=sm.families.NegativeBinomial(alpha=alpha), offset=offset
    ).fit(cov_type="HC1")
    res.alpha_estimate = alpha

    if not np.isfinite(res.bse).all():
        raise RuntimeError(f"{label}: standard errors did not converge")

    for term in terms:
        beta = res.params[term]
        se = res.bse[term]
        p = res.pvalues[term]
        coef_rows.append(
            {
                "region": region_label,
                "level": level,
                "model": label,
                "term": term,
                "coefficient": round(beta, 4),
                "std_error": round(se, 4),
                "rate_ratio": round(np.exp(beta), 4),
                "ci_low": round(np.exp(beta - 1.96 * se), 4),
                "ci_high": round(np.exp(beta + 1.96 * se), 4),
                "p_value": p,
                "significant_05": p < 0.05,
            }
        )

    main = res.params["pct_hispanic_10"]
    main_p = res.pvalues["pct_hispanic_10"]
    summary_rows.append(
        {
            "region": region_label,
            "level": level,
            "model": label,
            "n_units": len(d),
            "total_cameras": int(y.sum()),
            "pct_hispanic_rate_ratio": round(np.exp(main), 4),
            "pct_change_per_10pt": round(100 * (np.exp(main) - 1), 1),
            "p_value": main_p,
            "significant_05": main_p < 0.05,
            "alpha_overdispersion": round(res.alpha_estimate, 3),
            "log_likelihood": round(res.llf, 1),
            "pseudo_r2": round(1 - res.deviance / res.null_deviance, 4),
            "note": note,
        }
    )

    direction = "more" if main > 0 else "fewer"
    print(
        f"  {label:16s} n={len(d):>5,}  "
        f"rate ratio {np.exp(main):.3f} ({100 * (np.exp(main) - 1):+.1f}% "
        f"{direction} cameras per +10pt Hispanic), p={fmt_p(main_p)}"
    )
    return res, d


def city_dummies(df: pd.DataFrame, min_units: int = 10) -> tuple[pd.DataFrame, list[str]]:
    """City fixed effects for cities with enough units; the rest pooled."""
    counts = df["city"].value_counts()
    big = counts[counts >= min_units].index
    city = df["city"].where(df["city"].isin(big), "(other/small city)")
    dummies = pd.get_dummies(city, prefix="city", drop_first=True).astype(float)
    return dummies, list(dummies.columns)


def spatial_checks(res, d: pd.DataFrame, units, region_label: str, level: str):
    """Moran's I on residuals; spatial lag model if autocorrelation is present."""
    geo = units.set_index("GEOID").loc[d["GEOID"]]
    gdf = geo.reset_index()

    w = Queen.from_dataframe(gdf, use_index=False, silence_warnings=True)
    w.transform = "r"
    islands = len(w.islands)

    resid = res.resid_pearson if hasattr(res, "resid_pearson") else res.resid_response
    mi = Moran(np.asarray(resid), w, permutations=999)

    print(
        f"  Moran's I on residuals: {mi.I:.3f} (p={fmt_p(mi.p_sim)}), "
        f"{islands} islands"
    )

    row = {
        "region": region_label,
        "level": level,
        "test": "Moran's I on M1 residuals",
        "statistic": round(mi.I, 4),
        "p_value": mi.p_sim,
        "n_units": len(gdf),
        "islands": islands,
        "interpretation": (
            "residuals clustered - spatial model warranted"
            if mi.p_sim < 0.05 and mi.I > 0
            else "no meaningful residual clustering"
        ),
    }

    lag_note = ""
    if mi.p_sim < 0.05:
        # Spatial lag cross-check on a transformed continuous outcome.
        y = np.log1p(d[OUTCOME].astype(float).values).reshape(-1, 1)
        X = d[BASE_TERMS].astype(float).values
        lag = GM_Lag(y, X, w=w, name_y="log1p_cameras", name_x=BASE_TERMS)
        beta = float(np.ravel(lag.betas)[1])
        se = float(np.sqrt(lag.vm[1, 1]))
        z = beta / se
        from scipy.stats import norm

        p = 2 * (1 - norm.cdf(abs(z)))
        rho = float(np.ravel(lag.betas)[-1])
        lag_note = (
            f"spatial lag: pct_hispanic_10 beta={beta:.4f} (p={fmt_p(p)}), "
            f"rho={rho:.3f}"
        )
        print(f"  {lag_note}")
        spatial_rows.append(
            {
                "region": region_label,
                "level": level,
                "test": "Spatial lag model (log1p outcome)",
                "statistic": round(beta, 4),
                "p_value": p,
                "n_units": len(gdf),
                "islands": islands,
                "interpretation": (
                    f"rho={rho:.3f}; "
                    + (
                        "Hispanic share still positive and significant"
                        if beta > 0 and p < 0.05
                        else "Hispanic share not significantly positive"
                    )
                ),
            }
        )

    row["interpretation"] += f" {lag_note}".rstrip()
    spatial_rows.append(row)


def main() -> int:
    for region in REGIONS:
        print(f"\n{region.label} - negative binomial, outcome = {OUTCOME}")
        df = model_frame(region.key, "tract")
        units = load_units(region.key, "tract")[["GEOID", "geometry"]]

        res1, d1 = fit_nb(df, BASE_TERMS, "M1 base", region.label, "tract")

        crime_df = df[df["crime_data_available"]].copy()
        fit_nb(
            crime_df,
            BASE_TERMS + ["crime_per_1k"],
            "M2 +crime",
            region.label,
            "tract",
            note="restricted to tracts inside the crime-reporting city",
        )

        dummies, dummy_cols = city_dummies(df)
        df_fe = pd.concat([df.reset_index(drop=True),
                           dummies.reset_index(drop=True)], axis=1)
        fit_nb(
            df_fe,
            BASE_TERMS + dummy_cols,
            "M3 within-city",
            region.label,
            "tract",
            note=f"city fixed effects, {len(dummy_cols) + 1} city groups",
        )

        bg = model_frame(region.key, "bg")
        fit_nb(bg, BASE_TERMS, "M4 block group", region.label, "bg",
               note="robustness check at block-group level")

        spatial_checks(res1, d1, units, region.label, "tract")

    save_table(pd.DataFrame(coef_rows), "model_coefficients.csv")
    save_table(pd.DataFrame(summary_rows), "model_summary.csv")
    save_table(pd.DataFrame(spatial_rows), "spatial_diagnostics.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
