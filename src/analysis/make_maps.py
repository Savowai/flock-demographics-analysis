"""Phase 5: interactive maps.

One Folium map per region: tracts shaded by percent Hispanic/Latino, Flock
cameras on top, with toggleable layers for camera density, retailers and
day-labor candidates.

Run: .venv/bin/python src/analysis/make_maps.py
Writes: outputs/maps/{region}_cameras_demographics.html
"""

from __future__ import annotations

import sys

import branca.colormap as cm
import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import MarkerCluster

from analysis_common import PROJECT_ROOT, RAW, REGIONS, load_units

MAPS = PROJECT_ROOT / "outputs" / "maps"


def add_choropleth(m, units: gpd.GeoDataFrame, column: str, caption: str,
                   name: str, palette: str, show: bool = True):
    values = units[column].dropna()
    colormap = getattr(cm.linear, palette).scale(
        float(values.min()), float(values.quantile(0.98))
    )
    colormap.caption = caption

    folium.GeoJson(
        units.to_crs(4326),
        name=name,
        show=show,
        style_function=lambda feat, col=column, cmap=colormap: {
            "fillColor": (
                cmap(feat["properties"][col])
                if feat["properties"][col] is not None
                else "#cccccc"
            ),
            "color": "#666666",
            "weight": 0.3,
            "fillOpacity": 0.65,
        },
        highlight_function=lambda _: {"weight": 2, "color": "#000000"},
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "GEOID", "city", "pct_hispanic", "pop_total", "median_hh_income",
                "cameras_flock", "road_miles", "cameras_per_road_mile",
            ],
            aliases=[
                "Tract", "City", "% Hispanic/Latino", "Population",
                "Median income", "Flock cameras", "Arterial road-miles",
                "Cameras per road-mile",
            ],
            localize=True,
        ),
    ).add_to(m)
    colormap.add_to(m)


def build(region) -> None:
    units = load_units(region.key, "tract").to_crs(4326)
    units["cameras_per_road_mile"] = units["cameras_per_road_mile"].round(3)
    units["pct_hispanic"] = units["pct_hispanic"].round(1)

    centre = [units.geometry.centroid.y.mean(), units.geometry.centroid.x.mean()]
    m = folium.Map(location=centre, zoom_start=10, tiles="OpenStreetMap")

    add_choropleth(
        m, units, "pct_hispanic", "% Hispanic or Latino (ACS 2020-2024)",
        "Tracts: % Hispanic/Latino", "YlOrRd_09", show=True,
    )
    add_choropleth(
        m, units, "cameras_per_road_mile", "Flock cameras per arterial road-mile",
        "Tracts: camera density", "PuBu_09", show=False,
    )

    # Cameras, split by who operates them.
    cams = pd.read_csv(RAW / "osm" / f"alpr_{region.key}.csv")
    cams["operator"] = cams["operator"].fillna("(no operator tag)")
    flock = cams[cams["is_flock"]]
    retail = flock[flock["operator"].str.contains(r"home\s*depot|lowe'?s", case=False)]
    other = flock[~flock.index.isin(retail.index)]

    for label, frame, colour, show in [
        ("Flock cameras (not retail-operated)", other, "#1f4e79", True),
        ("Flock cameras (store-operated)", retail, "#b03060", False),
        ("Other ALPR (non-Flock)", cams[~cams["is_flock"]], "#777777", False),
    ]:
        layer = folium.FeatureGroup(name=f"{label} ({len(frame)})", show=show)
        cluster = MarkerCluster(disable_clustering_at_zoom=14).add_to(layer)
        for _, c in frame.iterrows():
            folium.CircleMarker(
                location=[c["lat"], c["lon"]],
                radius=3,
                color=colour,
                fill=True,
                fill_opacity=0.85,
                popup=folium.Popup(
                    f"<b>{c.get('manufacturer') or c.get('brand') or 'ALPR'}</b><br>"
                    f"Operator: {c['operator']}<br>"
                    f"OSM {c['osm_type']} {c['osm_id']}<br>"
                    f"Mapped as of {c['query_date']}",
                    max_width=260,
                ),
            ).add_to(cluster)
        layer.add_to(m)

    # Retailers
    stores = pd.read_csv(RAW / "osm" / f"retailers_{region.key}.csv")
    store_layer = folium.FeatureGroup(
        name=f"Home Depot / Lowe's ({len(stores)})", show=False
    )
    for _, s in stores.iterrows():
        folium.Marker(
            location=[s["lat"], s["lon"]],
            icon=folium.Icon(color="orange", icon="wrench", prefix="fa"),
            popup=f"{s['chain']}<br>{s.get('addr') or ''}",
        ).add_to(store_layer)
    store_layer.add_to(m)

    controls = pd.read_csv(RAW / "osm" / f"control_retailers_{region.key}.csv")
    control_layer = folium.FeatureGroup(
        name=f"Control big-box stores ({len(controls)})", show=False
    )
    for _, s in controls.iterrows():
        folium.Marker(
            location=[s["lat"], s["lon"]],
            icon=folium.Icon(color="lightgray", icon="cart-shopping", prefix="fa"),
            popup=f"{s['chain']}",
        ).add_to(control_layer)
    control_layer.add_to(m)

    # Day-labor candidates (unverified)
    labor = pd.read_csv(RAW / "day_labor_sites.csv")
    labor = labor[labor["region"] == region.key]
    if len(labor):
        labor_layer = folium.FeatureGroup(
            name=f"Day-labor candidates, UNVERIFIED ({len(labor)})", show=False
        )
        for _, s in labor.iterrows():
            folium.Marker(
                location=[s["lat"], s["lon"]],
                icon=folium.Icon(color="green", icon="person", prefix="fa"),
                popup=f"<b>{s['name']}</b><br>{s['address']}<br>"
                      f"<i>unverified candidate</i><br>Source: {s['source'][:80]}",
            ).add_to(labor_layer)
        labor_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    title = (
        f'<div style="position:fixed;top:10px;left:60px;z-index:9999;'
        f'background:white;padding:8px 12px;border:1px solid #999;'
        f'border-radius:4px;font-family:sans-serif;max-width:420px">'
        f'<b>{region.label}</b><br>'
        f'<span style="font-size:12px">Flock ALPR cameras and Hispanic/Latino '
        f'population share by census tract.<br>Cameras: OpenStreetMap/DeFlock, '
        f'queried {flock["query_date"].iloc[0]} - crowdsourced and incomplete.'
        f'</span></div>'
    )
    m.get_root().html.add_child(folium.Element(title))

    MAPS.mkdir(parents=True, exist_ok=True)
    out = MAPS / f"{region.key}_cameras_demographics.html"
    m.save(str(out))
    print(f"  {region.label}: {len(units):,} tracts, {len(flock):,} Flock cameras "
          f"-> {out.name} ({out.stat().st_size / 1e6:.1f} MB)")


def main() -> int:
    print("Building interactive maps")
    for region in REGIONS:
        build(region)
    return 0


if __name__ == "__main__":
    sys.exit(main())
