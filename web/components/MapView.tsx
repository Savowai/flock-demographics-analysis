"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type RegionKey = "la" | "king";

const REGIONS: Record<RegionKey, { label: string; center: [number, number]; zoom: number }> = {
  la: { label: "Los Angeles County", center: [-118.25, 34.05], zoom: 8.6 },
  king: { label: "King County (Seattle)", center: [-122.2, 47.45], zoom: 9.2 },
};

type Shading = "pct_hispanic" | "cameras_per_road_mile";

const SHADING: Record<Shading, { label: string; stops: [number, string][]; unit: string }> = {
  pct_hispanic: {
    label: "% Hispanic or Latino",
    unit: "%",
    stops: [
      [0, "#fff7ec"],
      [20, "#fee8c8"],
      [40, "#fdbb84"],
      [60, "#fc8d59"],
      [80, "#d7301f"],
      [100, "#7f0000"],
    ],
  },
  cameras_per_road_mile: {
    label: "Flock cameras per mile of major road",
    unit: "",
    stops: [
      [0, "#f7fbff"],
      [0.25, "#d0e1f2"],
      [0.5, "#94c4df"],
      [1, "#4a98c9"],
      [2, "#1764ab"],
      [4, "#08306b"],
    ],
  },
};

// OpenStreetMap raster tiles: no API key, no account, works on any host.
const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.55 } }],
};

export default function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [region, setRegion] = useState<RegionKey>("king");
  const [shading, setShading] = useState<Shading>("pct_hispanic");
  const [showCameras, setShowCameras] = useState(true);
  const [showHomeImprovement, setShowHomeImprovement] = useState(false);
  const [showControlStores, setShowControlStores] = useState(false);
  const [showDayLabor, setShowDayLabor] = useState(false);
  const [ready, setReady] = useState(false);

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: REGIONS[region].center,
      zoom: REGIONS[region].zoom,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => setReady(true));
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load the selected region's layers.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;

    const ids = ["tracts-fill", "tracts-line", "cameras",
                 "stores-home-improvement", "stores-control", "daylabor"];
    ids.forEach((id) => map.getLayer(id) && map.removeLayer(id));
    ["tracts", "cameras-src", "stores-src", "daylabor-src"].forEach(
      (id) => map.getSource(id) && map.removeSource(id),
    );

    map.addSource("tracts", { type: "geojson", data: `/data/tracts_${region}.geojson` });
    map.addSource("cameras-src", { type: "geojson", data: `/data/cameras_${region}.geojson` });
    map.addSource("stores-src", { type: "geojson", data: `/data/stores_${region}.geojson` });
    map.addSource("daylabor-src", { type: "geojson", data: `/data/daylabor_${region}.geojson` });

    map.addLayer({
      id: "tracts-fill",
      type: "fill",
      source: "tracts",
      paint: {
        "fill-color": [
          "interpolate",
          ["linear"],
          ["coalesce", ["get", shading], 0],
          ...SHADING[shading].stops.flat(),
        ] as unknown as maplibregl.ExpressionSpecification,
        "fill-opacity": 0.72,
      },
    });
    map.addLayer({
      id: "tracts-line",
      type: "line",
      source: "tracts",
      paint: { "line-color": "#64748b", "line-width": 0.3, "line-opacity": 0.6 },
    });

    map.addLayer({
      id: "cameras",
      type: "circle",
      source: "cameras-src",
      filter: ["!=", ["get", "category"], "other ALPR"],
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 14, 5],
        "circle-color": [
          "match",
          ["get", "category"],
          "Flock (store-operated)", "#b03060",
          "#12355b",
        ],
        "circle-stroke-width": 0.5,
        "circle-stroke-color": "#ffffff",
        "circle-opacity": 0.9,
      },
      layout: { visibility: showCameras ? "visible" : "none" },
    });

    map.addLayer({
      id: "stores-home-improvement",
      type: "circle",
      source: "stores-src",
      filter: ["==", ["get", "group"], "home improvement"],
      paint: {
        "circle-radius": 6,
        "circle-color": "#e07a21",
        "circle-stroke-width": 1.2,
        "circle-stroke-color": "#1f2937",
      },
      layout: { visibility: showHomeImprovement ? "visible" : "none" },
    });

    map.addLayer({
      id: "stores-control",
      type: "circle",
      source: "stores-src",
      filter: ["==", ["get", "group"], "control big-box"],
      paint: {
        "circle-radius": 5,
        "circle-color": "#94a3b8",
        "circle-stroke-width": 1,
        "circle-stroke-color": "#475569",
      },
      layout: { visibility: showControlStores ? "visible" : "none" },
    });

    map.addLayer({
      id: "daylabor",
      type: "circle",
      source: "daylabor-src",
      paint: {
        "circle-radius": 5,
        "circle-color": "#16a34a",
        "circle-stroke-width": 1,
        "circle-stroke-color": "#ffffff",
      },
      layout: { visibility: showDayLabor ? "visible" : "none" },
    });

    map.flyTo({ center: REGIONS[region].center, zoom: REGIONS[region].zoom, duration: 800 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region, ready]);

  // Recolour without reloading data.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !map.getLayer("tracts-fill")) return;
    map.setPaintProperty("tracts-fill", "fill-color", [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", shading], 0],
      ...SHADING[shading].stops.flat(),
    ] as unknown as maplibregl.ExpressionSpecification);
  }, [shading, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const toggles: [string, boolean][] = [
      ["cameras", showCameras],
      ["stores-home-improvement", showHomeImprovement],
      ["stores-control", showControlStores],
      ["daylabor", showDayLabor],
    ];
    toggles.forEach(([id, on]) => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
      }
    });
  }, [showCameras, showHomeImprovement, showControlStores, showDayLabor, ready]);

  // Popups.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;

    const popup = new maplibregl.Popup({ closeButton: false, maxWidth: "320px" });

    const onTractClick = (e: maplibregl.MapMouseEvent) => {
      const feature = map.queryRenderedFeatures(e.point, { layers: ["tracts-fill"] })[0];
      if (!feature) return;
      const p = feature.properties as Record<string, unknown>;
      const num = (v: unknown, digits = 1) =>
        v === null || v === undefined ? "—" : Number(v).toLocaleString(undefined, {
          maximumFractionDigits: digits,
        });
      popup
        .setLngLat(e.lngLat)
        .setHTML(
          `<div class="space-y-0.5">
             <div class="font-semibold text-ink">${p.city ?? "Tract"}</div>
             <div class="text-xs text-slate-500">GEOID ${p.GEOID}</div>
             <div class="pt-1">${num(p.pct_hispanic)}% Hispanic/Latino</div>
             <div>${num(p.pop_total, 0)} residents</div>
             <div>${p.median_hh_income ? "$" + num(p.median_hh_income, 0) + " median income" : "income not reported"}</div>
             <div class="pt-1 font-medium">${num(p.cameras_flock, 0)} Flock cameras</div>
             <div>${num(p.road_miles, 2)} miles of major road</div>
             <div class="mt-1 border-t border-slate-200 pt-1">
               <span class="font-medium">${num(p.cameras_per_road_mile, 2)}</span>
               cameras per mile of major road
             </div>
           </div>`,
        )
        .addTo(map);
    };

    map.on("click", "tracts-fill", onTractClick);
    map.on("mouseenter", "tracts-fill", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "tracts-fill", () => (map.getCanvas().style.cursor = ""));
    return () => {
      map.off("click", "tracts-fill", onTractClick);
    };
  }, [ready]);

  const legend = SHADING[shading];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg border border-rule bg-white p-1">
          {(Object.keys(REGIONS) as RegionKey[]).map((key) => (
            <button
              key={key}
              onClick={() => setRegion(key)}
              className={`min-h-[40px] rounded-md px-3 text-sm transition-colors duration-200 ${
                region === key ? "bg-ink text-white" : "text-slate-600 hover:text-ink"
              }`}
            >
              {REGIONS[key].label}
            </button>
          ))}
        </div>

        <select
          value={shading}
          onChange={(e) => setShading(e.target.value as Shading)}
          className="rounded-lg border border-rule bg-white px-3 py-2 text-sm"
        >
          {(Object.keys(SHADING) as Shading[]).map((key) => (
            <option key={key} value={key}>
              Shade by: {SHADING[key].label}
            </option>
          ))}
        </select>

        {[
          ["Flock cameras", showCameras, setShowCameras],
          ["Home Depot / Lowe's", showHomeImprovement, setShowHomeImprovement],
          ["Control stores (Target, Walmart…)", showControlStores, setShowControlStores],
          ["Day-labor candidates", showDayLabor, setShowDayLabor],
        ].map(([label, value, setter]) => (
          <label
            key={label as string}
            className="flex items-center gap-2 rounded-lg border border-rule bg-white px-3 py-2 text-sm"
          >
            <input
              type="checkbox"
              checked={value as boolean}
              onChange={(e) => (setter as (v: boolean) => void)(e.target.checked)}
            />
            {label as string}
          </label>
        ))}
      </div>

      <div className="relative overflow-hidden rounded-xl border border-rule">
        <div ref={containerRef} className="h-[620px] w-full" />
        <div className="absolute bottom-6 left-3 rounded-lg border border-rule bg-white/95 p-3 text-xs shadow">
          <div className="mb-1.5 font-medium text-slate-700">{legend.label}</div>
          <div className="flex items-center gap-1">
            {legend.stops.map(([value, color]) => (
              <div key={value} className="text-center">
                <div className="h-3 w-8" style={{ background: color }} />
                <div className="mt-0.5 text-[10px] text-slate-500">
                  {value}
                  {legend.unit}
                </div>
              </div>
            ))}
          </div>
          {(showCameras || showHomeImprovement || showControlStores || showDayLabor) && (
            <div className="mt-2.5 space-y-1.5 border-t border-rule pt-2">
              {showCameras && (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#12355b]" />
                    Flock camera
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#b03060]" />
                    camera owned by the store
                  </div>
                </>
              )}
              {showHomeImprovement && (
                <div className="flex items-center gap-1.5">
                  <span className="inline-block h-3 w-3 rounded-full border border-slate-800 bg-[#e07a21]" />
                  Home Depot / Lowe&apos;s
                </div>
              )}
              {showControlStores && (
                <div className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-full border border-slate-600 bg-[#94a3b8]" />
                  control store
                </div>
              )}
              {showDayLabor && (
                <div className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#16a34a]" />
                  day-labor candidate
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 rounded-lg border border-rule bg-white p-5 text-sm leading-6 text-slate-600 md:grid-cols-3">
        <div>
          <h2 className="font-serif text-base font-semibold text-ink">
            Reading the shading
          </h2>
          <p className="mt-1.5">
            <strong className="font-medium text-slate-700">
              Cameras per road-mile
            </strong>{" "}
            is cameras divided by miles of major road in that tract. A tract with
            more boulevards will hold more cameras for reasons unrelated to who
            lives there, so dividing by road mileage is the fair comparison.
          </p>
        </div>
        <div>
          <h2 className="font-serif text-base font-semibold text-ink">
            Which stores are shown
          </h2>
          <p className="mt-1.5">
            Not all retail — only the two groups the analysis compares.{" "}
            <strong className="font-medium text-slate-700">
              Home Depot and Lowe&apos;s
            </strong>{" "}
            are the ones being tested;{" "}
            <strong className="font-medium text-slate-700">control stores</strong>{" "}
            (Target, Walmart, Costco, Best Buy, Kohl&apos;s) are the comparison
            group, similar in size and siting but not day-labor hiring spots.
          </p>
        </div>
        <div>
          <h2 className="font-serif text-base font-semibold text-ink">
            What to be careful about
          </h2>
          <p className="mt-1.5">
            Camera locations are crowdsourced through DeFlock and OpenStreetMap,
            so coverage is incomplete. Cameras owned by a store are private
            placements and are excluded from the statistical models.
          </p>
        </div>
      </div>

      <p className="text-sm text-slate-500">
        Click any tract for its demographics and camera count.
      </p>
    </div>
  );
}
