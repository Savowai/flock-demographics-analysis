"""Phase 5b: static figures for the report.

Produces the maps and charts that carry the argument in `docs/report.md`:

  fig1_choropleth_{region}.png   % Hispanic by tract with camera locations
  fig2_camera_density_{region}.png  cameras per road-mile by tract
  fig3_bivariate_{region}.png    where high-Hispanic and high-camera overlap
  fig4_quartiles.png             camera density by Hispanic quartile, both regions
  fig5_scatter.png               tract-level relationship with fitted trend
  fig6_model_effects.png         model coefficients with confidence intervals
  fig7_retailer_test.png         home improvement vs control big-box

Run: .venv/bin/python src/analysis/make_figures.py
Writes: outputs/figures/*.png
"""

from __future__ import annotations

import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from analysis_common import PROJECT_ROOT, RAW, REGIONS, TABLES, load_units  # noqa: E402

FIGURES = PROJECT_ROOT / "outputs" / "figures"
DPI = 160

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


# LA County includes Catalina and San Clemente islands, ~40 miles offshore.
# Keeping them in frame shrinks the populated mainland to a corner, so map
# extents are clipped to the mainland and the figure says so.
MAINLAND_MIN_LAT = {"la": 33.6, "king": -90.0}


def set_mainland_extent(ax, units, region) -> bool:
    """Limit axes to mainland tracts. Returns True if anything was cropped."""
    latlon = units.to_crs(4326)
    mainland = latlon[latlon.geometry.centroid.y >= MAINLAND_MIN_LAT[region.key]]
    if len(mainland) == len(latlon):
        return False

    bounds = units.loc[mainland.index].total_bounds  # projected CRS
    pad_x = (bounds[2] - bounds[0]) * 0.02
    pad_y = (bounds[3] - bounds[1]) * 0.02
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    return True


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path.relative_to(PROJECT_ROOT)}")


def cameras_gdf(region):
    import geopandas as gpd
    from shapely.geometry import Point

    cams = pd.read_csv(RAW / "osm" / f"alpr_{region.key}.csv")
    cams["operator"] = cams["operator"].fillna("")
    flock = cams[cams["is_flock"]]
    nonretail = flock[
        ~flock["operator"].str.contains(r"home\s*depot|lowe'?s", case=False)
    ]
    return gpd.GeoDataFrame(
        nonretail,
        geometry=[Point(xy) for xy in zip(nonretail["lon"], nonretail["lat"])],
        crs="EPSG:4326",
    ).to_crs(region.crs)


def fig_choropleth(region, units, cams):
    fig, ax = plt.subplots(figsize=(8, 8))
    units.plot(
        column="pct_hispanic", cmap="YlOrRd", linewidth=0.05, edgecolor="#999999",
        legend=True, ax=ax,
        legend_kwds={"label": "% Hispanic or Latino", "shrink": 0.55},
        missing_kwds={"color": "#eeeeee"},
    )
    cams.plot(ax=ax, color="#12355b", markersize=3, alpha=0.75)
    ax.set_title(
        f"{region.label}\nHispanic/Latino share by tract, with Flock ALPR cameras",
        loc="left",
    )
    cropped = set_mainland_extent(ax, units, region)
    ax.set_axis_off()
    ax.legend(
        handles=[Line2D([], [], marker="o", color="#12355b", linestyle="",
                        markersize=4, label=f"Flock camera ({len(cams):,})")],
        loc="lower left", frameon=False,
    )
    note = ("Cameras: OpenStreetMap/DeFlock, crowdsourced and incomplete. "
            "Demographics: ACS 2020-2024.")
    if cropped:
        note += " View cropped to the mainland; offshore islands omitted."
    fig.text(0.01, 0.02, note, fontsize=7, color="#555555")
    save(fig, f"fig1_choropleth_{region.key}.png")


def fig_density(region, units):
    fig, ax = plt.subplots(figsize=(8, 8))
    units.plot(
        column="cameras_per_road_mile", cmap="PuBu", scheme=None, linewidth=0.05,
        edgecolor="#999999", legend=True, ax=ax,
        vmin=0, vmax=float(units["cameras_per_road_mile"].quantile(0.97)),
        legend_kwds={"label": "Flock cameras per arterial road-mile", "shrink": 0.55},
        missing_kwds={"color": "#eeeeee"},
    )
    ax.set_title(f"{region.label}\nCamera density, normalised by arterial roads",
                 loc="left")
    set_mainland_extent(ax, units, region)
    ax.set_axis_off()
    save(fig, f"fig2_camera_density_{region.key}.png")


def fig_bivariate(region, units):
    """Two-way split: is a tract above the median on each measure?"""
    d = units.copy()
    hisp_med = d["pct_hispanic"].median()
    cam_med = d.loc[d["cameras_per_road_mile"] > 0, "cameras_per_road_mile"].median()

    def category(row):
        if pd.isna(row["pct_hispanic"]) or pd.isna(row["cameras_per_road_mile"]):
            return "no data"
        high_h = row["pct_hispanic"] >= hisp_med
        high_c = row["cameras_per_road_mile"] >= cam_med
        if high_h and high_c:
            return "high Hispanic, high cameras"
        if high_h:
            return "high Hispanic, low cameras"
        if high_c:
            return "low Hispanic, high cameras"
        return "low Hispanic, low cameras"

    d["category"] = d.apply(category, axis=1)
    colours = {
        "high Hispanic, high cameras": "#6b0f1a",
        "high Hispanic, low cameras": "#e8a33d",
        "low Hispanic, high cameras": "#2c6e91",
        "low Hispanic, low cameras": "#e8e8e8",
        "no data": "#ffffff",
    }

    fig, ax = plt.subplots(figsize=(8, 8))
    for cat, colour in colours.items():
        subset = d[d["category"] == cat]
        if len(subset):
            subset.plot(ax=ax, color=colour, linewidth=0.05, edgecolor="#999999")
    counts = d["category"].value_counts()
    ax.set_title(
        f"{region.label}\nWhere high Hispanic share and high camera density overlap\n"
        f"(split at tract medians: {hisp_med:.0f}% Hispanic, "
        f"{cam_med:.2f} cameras/road-mile)",
        loc="left",
    )
    set_mainland_extent(ax, d, region)
    ax.set_axis_off()
    ax.legend(
        handles=[
            Patch(facecolor=c, edgecolor="#999999",
                  label=f"{cat} ({counts.get(cat, 0)})")
            for cat, c in colours.items() if cat != "no data"
        ],
        loc="lower left", frameon=False, fontsize=8,
    )
    save(fig, f"fig3_bivariate_{region.key}.png")


def fig_quartiles():
    q = pd.read_csv(TABLES / "descriptive_quartiles.csv")
    q = q[q["level"] == "tract"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, (region_label, g) in zip(axes, q.groupby("region", sort=False)):
        bars = ax.bar(
            g["quartile"].astype(str), g["cameras_per_road_mile"],
            color=["#d9d9d9", "#bdbdbd", "#f4a261", "#c1272d"],
        )
        for bar, val, rng in zip(bars, g["cameras_per_road_mile"],
                                 g["pct_hispanic_range"]):
            ax.text(bar.get_x() + bar.get_width() / 2, val,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=8)
            ax.text(bar.get_x() + bar.get_width() / 2, 0.003,
                    f"{rng}%", ha="center", va="bottom", fontsize=7,
                    color="#333333", rotation=90)
        ratio = g["ratio_q4_to_q1_per_road_mile"].iloc[0]
        ax.set_title(f"{region_label}\nQ4 vs Q1: {ratio}x", loc="left")
        ax.set_xlabel("Hispanic/Latino share, quartile (1 = lowest)")
        ax.set_ylabel("Flock cameras per arterial road-mile")
    fig.suptitle(
        "Camera density by neighbourhood Hispanic share - opposite directions "
        "in the two counties",
        x=0.01, ha="left", fontsize=12,
    )
    fig.tight_layout()
    save(fig, "fig4_quartiles.png")


def fig_scatter():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, region in zip(axes, REGIONS):
        units = load_units(region.key, "tract")
        d = pd.DataFrame(units.drop(columns="geometry"))
        d = d[(d["road_miles"] > 0) & d["pct_hispanic"].notna()]
        rate = d["cameras_flock_nonretail"] / d["road_miles"]

        ax.scatter(d["pct_hispanic"], rate, s=6, alpha=0.3, color="#12355b",
                   edgecolors="none")
        # Binned means make the trend legible through the scatter.
        bins = np.arange(0, 101, 10)
        idx = np.digitize(d["pct_hispanic"], bins) - 1
        means = [rate[idx == b].mean() for b in range(len(bins) - 1)]
        centres = bins[:-1] + 5
        ax.plot(centres, means, color="#c1272d", marker="o", markersize=4,
                linewidth=2, label="mean per 10-point band")

        r = np.corrcoef(d["pct_hispanic"], rate)[0, 1]
        ax.set_title(f"{region.label}  (r = {r:+.3f})", loc="left")
        ax.set_xlabel("% Hispanic or Latino in tract")
        ax.set_ylabel("Flock cameras per road-mile")
        ax.set_ylim(0, float(np.nanquantile(rate, 0.98)))
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Tract-level relationship, cameras normalised by arterial roads",
                 x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "fig5_scatter.png")


def fig_model_effects():
    coef = pd.read_csv(TABLES / "model_coefficients.csv")
    coef = coef[coef["term"] == "pct_hispanic_10"]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels, y = [], 0
    for region_label, g in coef.groupby("region", sort=False):
        colour = "#c1272d" if "Los Angeles" in region_label else "#12355b"
        for _, row in g.iterrows():
            ax.plot([row["ci_low"], row["ci_high"]], [y, y], color=colour, lw=2)
            ax.plot(row["rate_ratio"], y, "o", color=colour, ms=7)
            star = "*" if row["significant_05"] else ""
            ax.text(row["ci_high"] + 0.02, y,
                    f"{row['rate_ratio']:.2f}{star}", va="center", fontsize=8)
            labels.append(f"{region_label.split(',')[0]} - {row['model']}")
            y += 1
        y += 0.5

    ax.axvline(1.0, color="#666666", linestyle="--", lw=1)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel(
        "Rate ratio per +10 percentage points Hispanic/Latino\n"
        "(1.0 = no difference; >1 more cameras, <1 fewer)"
    )
    ax.set_title(
        "Negative binomial models, cameras per arterial road-mile\n"
        "* = significant at p<0.05; bars are 95% confidence intervals",
        loc="left",
    )
    fig.tight_layout()
    save(fig, "fig6_model_effects.png")


def fig_retailer():
    comp = pd.read_csv(TABLES / "retailer_daylabor_comparison.csv")
    comp = comp[comp["test"].str.contains("control big-box")]

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(comp))
    width = 0.36
    ax.bar(x - width / 2, 100 * comp["camera_rate_home_improvement"], width,
           label="Home Depot / Lowe's", color="#c1272d")
    ax.bar(x + width / 2, 100 * comp["camera_rate_control"], width,
           label="Control big-box (Target, Walmart, Costco, Best Buy, Kohl's)",
           color="#9fb8c8")

    for i, row in enumerate(comp.itertuples()):
        ax.text(i - width / 2, 100 * row.camera_rate_home_improvement + 1,
                f"{100 * row.camera_rate_home_improvement:.0f}%",
                ha="center", fontsize=9)
        ax.text(i + width / 2, 100 * row.camera_rate_control + 1,
                f"{100 * row.camera_rate_control:.0f}%", ha="center", fontsize=9)
        ax.text(i, 100 * row.camera_rate_home_improvement + 6,
                f"odds ratio {row.odds_ratio:.1f}x", ha="center", fontsize=9,
                fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([r.split(",")[0] for r in comp["region"]])
    ax.set_ylabel("% of stores with a non-chain Flock camera within 150 m")
    ax.set_ylim(0, 62)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title(
        "Home improvement stores vs comparable big-box stores",
        loc="left",
    )
    fig.tight_layout()
    save(fig, "fig7_retailer_test.png")


def main() -> int:
    print("Building figures")
    for region in REGIONS:
        units = load_units(region.key, "tract")
        cams = cameras_gdf(region)
        fig_choropleth(region, units, cams)
        fig_density(region, units)
        fig_bivariate(region, units)

    fig_quartiles()
    fig_scatter()
    fig_model_effects()
    fig_retailer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
