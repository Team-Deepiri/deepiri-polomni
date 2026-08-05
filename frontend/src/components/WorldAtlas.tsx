import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type WorldAtlas, type WorldMethodInfo } from "../api/client";

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#0d1117" } }],
};

const METHOD_COLORS: Record<string, string> = {
  Transit: "#58a6ff",
  "Radial Velocity": "#3fb950",
  Microlensing: "#d29922",
  Imaging: "#ff7043",
};

function teffColor(teff: number | null): string {
  if (teff == null) return "#8b949e";
  if (teff < 3500) return "#ff7043"; // M — cool orange
  if (teff < 5200) return "#f0b45d"; // K
  if (teff < 6000) return "#ffd88a"; // G — sun-like
  if (teff < 7350) return "#e6edf3"; // F
  return "#79c0ff"; // A/B — hot blue
}

function ringGeoJSON(worlds: WorldAtlas): GeoJSON.FeatureCollection {
  const { scar_ring, axis_marker } = worlds;
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { kind: "scar_ring" },
        geometry: {
          type: "LineString",
          coordinates: scar_ring.lon.map((lon, i) => [lon, scar_ring.lat[i]]),
        },
      },
      {
        type: "Feature",
        properties: { kind: "preferred_axis" },
        geometry: {
          type: "Point",
          coordinates: [axis_marker.lon, axis_marker.lat],
        },
      },
    ],
  };
}

export default function WorldAtlas({ height = 520 }: { height?: number }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [worlds, setWorlds] = useState<WorldAtlas | null>(null);
  const [nside, setNside] = useState(32);
  const [weight, setWeight] = useState("count");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [colorBy, setColorBy] = useState<"teff" | "method">("teff");

  const load = useCallback(
    async (ns: number, wt: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.cosmosWorlds({ nside: ns, weight: wt, nEnsemble: 40 });
        setWorlds(data);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    load(nside, weight);
  }, [nside, weight, load]);

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: EMPTY_STYLE,
      center: [60, 10],
      zoom: 0.6,
      maxZoom: 4,
      minZoom: 0.2,
      attributionControl: false,
      projection: { type: "globe" },
    } as maplibregl.MapOptions);
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

    const onReady = () => {
      if (cancelled || !worlds) return;

      const pts = worlds.points;
      const coords = pts.lon.map((lon, i) => [lon, pts.lat[i]]);
      const features = coords.map((c, i) => ({
        type: "Feature",
        properties: {
          name: pts.name[i],
          host: pts.host[i],
          method: pts.method[i],
          period_days: pts.period_days[i],
          st_teff: pts.st_teff[i],
          radius_earth: pts.radius_earth[i],
          disc_year: pts.disc_year[i],
          color: colorBy === "teff" ? teffColor(pts.st_teff[i]) : METHOD_COLORS[pts.method[i]] ?? "#8b949e",
        },
        geometry: { type: "Point", coordinates: c },
      }));

      if (map.getSource("worlds")) {
        map.removeLayer("worlds-layer");
        map.removeSource("worlds");
      }
      if (map.getSource("rble-overlays")) {
        map.removeLayer("scar-ring");
        map.removeLayer("axis-marker");
        map.removeSource("rble-overlays");
      }

      map.addSource("worlds", {
        type: "geojson",
        data: { type: "FeatureCollection", features } as unknown as GeoJSON.FeatureCollection,
      });
      map.addLayer({
        id: "worlds-layer",
        type: "circle",
        source: "worlds",
        paint: {
          "circle-radius": 2.4,
          "circle-color": ["get", "color"],
          "circle-opacity": 0.85,
          "circle-stroke-color": "#010409",
          "circle-stroke-width": 0.5,
        },
      });

      map.addSource("rble-overlays", {
        type: "geojson",
        data: ringGeoJSON(worlds),
      });
      map.addLayer({
        id: "scar-ring",
        type: "line",
        source: "rble-overlays",
        filter: ["==", ["get", "kind"], "scar_ring"],
        paint: { "line-color": "#ff7043", "line-width": 3, "line-opacity": 0.95 },
      });
      map.addLayer({
        id: "axis-marker",
        type: "circle",
        source: "rble-overlays",
        filter: ["==", ["get", "kind"], "preferred_axis"],
        paint: {
          "circle-radius": 10,
          "circle-color": "#3fb950",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });

      map.on("click", "worlds-layer", (e) => {
        const feat = e.features?.[0] as { properties?: Record<string, unknown> } | undefined;
        if (!feat?.properties) return;
        const p = feat.properties;
        new maplibregl.Popup({ closeButton: true, closeOnClick: false })
          .setLngLat((e.lngLat as { lat: number; lng: number }) ?? [0, 0])
          .setHTML(
            `<div class="world-popup">
               <strong>${p.name}</strong><br/>
               host: ${p.host}<br/>
               method: ${p.method} (${p.disc_year})<br/>
               period: ${p.period_days ?? "—"} d · R<sub>⊕</sub>: ${p.radius_earth ?? "—"}<br/>
               T<sub>eff</sub>: ${p.st_teff ?? "—"} K
             </div>`,
          )
          .addTo(map);
      });
      map.on("mouseenter", "worlds-layer", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "worlds-layer", () => {
        map.getCanvas().style.cursor = "";
      });

      (map as maplibregl.Map & { setFog?: (f: Record<string, unknown>) => void }).setFog?.({
        color: "#0d1117",
        "high-color": "#161b22",
        "horizon-blend": 0.08,
        "space-color": "#010409",
        "star-intensity": 0.5,
      });
    };

    if (map.isStyleLoaded()) onReady();
    else map.once("load", onReady);

    return () => {
      cancelled = true;
      map.remove();
      mapRef.current = null;
    };
  }, [worlds, colorBy]);

  const scan = worlds?.scan;
  const methods = worlds?.methods;
  const methodRows = methods
    ? Object.entries(methods).sort((a, b) => b[1].n_worlds - a[1].n_worlds)
    : [];

  return (
    <section className="world-atlas">
      <div className="cosmos-header">
        <div>
          <h2>World Atlas — NASA Exoplanet Archive</h2>
          <p className="cosmos-sub">
            {worlds
              ? `${worlds.catalog.n_worlds} confirmed worlds · ${worlds.catalog.n_hosts} host stars · RBLE scan + footprint-matched null`
              : "Real sky positions of confirmed exoplanets, scanned with RBLE"}
          </p>
        </div>
        <div className="cosmos-actions">
          <select
            className="proj-select"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          >
            <option value="count">Count density</option>
            <option value="teff">T_eff-weighted</option>
            <option value="period">log P-weighted</option>
          </select>
          <select
            className="proj-select"
            value={String(nside)}
            onChange={(e) => setNside(Number(e.target.value))}
          >
            <option value="16">NSIDE 16</option>
            <option value="32">NSIDE 32</option>
            <option value="64">NSIDE 64</option>
          </select>
          <select
            className="proj-select"
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as "teff" | "method")}
          >
            <option value="teff">Color: host T_eff</option>
            <option value="method">Color: discovery method</option>
          </select>
          <button onClick={() => load(nside, weight)}>Refresh</button>
        </div>
      </div>

      {error && <p className="error cosmos-error">{error}</p>}
      {loading && <div className="sky-maplibre-loading">Scanning real worlds…</div>}

      <div className="cosmos-grid-v2">
        <div className="card cosmos-dual cosmos-sky-hero">
          <div className="sky-maplibre-title">All confirmed worlds on the celestial sphere</div>
          <div className="sky-maplibre-sub">
            {worlds && (
              <span>
                S_RBLE={scan?.rble_score.toFixed(4)} · null σ={scan?.null_sigma_significance.toFixed(1)}
                · S_order={worlds.alignment.order_parameter_s.toFixed(3)} · Tr(Q)=
                {worlds.alignment.trace.toFixed(6)}
              </span>
            )}
          </div>
          <div className="sky-maplibre-canvas" style={{ height }} ref={containerRef} />
          <div className="sky-maplibre-legend">
            {colorBy === "teff" ? (
              <>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#ff7043" }} /> M cool
                </span>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#ffd88a" }} /> G sun-like
                </span>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#79c0ff" }} /> A/B hot
                </span>
              </>
            ) : (
              <>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#58a6ff" }} /> Transit
                </span>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#3fb950" }} /> Radial vel
                </span>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#d29922" }} /> Microlens
                </span>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "#ff7043" }} /> Imaging
                </span>
              </>
            )}
            <span className="legend-item">
              <span className="legend-swatch ring" /> RBLE scar ring
            </span>
            <span className="legend-item">
              <span className="legend-swatch axis" /> Preferred axis
            </span>
          </div>
        </div>

        <div className="cosmos-side">
          <div className="card cosmos-metrics">
            <h3>Scan (weight={weight})</h3>
            {scan && (
              <>
                <p>
                  S_RBLE <strong>{scan.rble_score.toFixed(4)}</strong>
                </p>
                <p>
                  axis [{scan.preferred_axis.map((v) => v.toFixed(2)).join(", ")}]
                </p>
                <p>
                  Footprint null μ={scan.null_mu.toFixed(3)} σ={scan.null_sigma.toFixed(3)} →{" "}
                  <strong>{scan.null_sigma_significance.toFixed(1)}σ</strong>
                </p>
                <p>
                  Axis ↔ Galactic pole{" "}
                  <strong>{scan.separation_from_galactic_pole_deg.toFixed(1)}°</strong>
                  <span className="muted"> (90° = in-plane)</span>
                </p>
              </>
            )}
            {worlds?.alignment && (
              <>
                <h3>Nematic order (all worlds)</h3>
                <p>
                  S = {worlds.alignment.order_parameter_s.toFixed(3)}{" "}
                  <span className="muted">(0 isotropic → 1 aligned)</span>
                </p>
                <p>
                  λ = [{worlds.alignment.eigenvalues.map((v) => v.toFixed(3)).join(", ")}]
                </p>
              </>
            )}
          </div>

          <div className="card progress-log">
            <h3>Selection-bias audit by discovery method</h3>
            <div className="log-scroll">
              <table className="world-method-table">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>N</th>
                    <th>S</th>
                    <th>↔ Gal. pole</th>
                  </tr>
                </thead>
                <tbody>
                  {methodRows.map(([name, info]) => {
                    const m = info as WorldMethodInfo;
                    return (
                      <tr key={name}>
                        <td>
                          <span
                            className="legend-swatch"
                            style={{ background: METHOD_COLORS[name] ?? "#8b949e", display: "inline-block", verticalAlign: "middle" }}
                          />{" "}
                          {name}
                        </td>
                        <td>{m.n_worlds}</td>
                        <td>{m.order_parameter_s.toFixed(3)}</td>
                        <td>{m.separation_from_galactic_pole_deg.toFixed(0)}°</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="muted" style={{ marginTop: 8 }}>
                A genuine world scar must survive the footprint-matched null AND persist
                across methods with different sky coverage. Sky-complete radial-velocity
                worlds are near-isotropic (S≈0); microlensing worlds are ordered in the
                Galactic plane.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
