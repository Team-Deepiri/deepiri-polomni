import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, type CrossSkyReport, type WorldAtlas, type WorldDipoleRefs, type WorldMethodInfo, type WorldSpectrum } from "../api/client";
import BubbleSearchCard from "./BubbleSearchCard";

const SPECTRUM_W = 260;
const SPECTRUM_H = 110;
const SPECTRUM_PAD = { top: 8, right: 6, bottom: 18, left: 30 };

function WorldSpectrumChart({ spectrum }: { spectrum: WorldSpectrum }) {
  const { ell, pseudo, null: band } = spectrum;
  const lCut = Math.max(...ell.filter((l) => l <= 40), 8);

  const el = ell.slice(0, lCut + 1);
  const obs = pseudo.slice(0, lCut + 1);
  const p50 = band.p50.slice(0, lCut + 1);
  const p16 = band.p16.slice(0, lCut + 1);
  const p84 = band.p84.slice(0, lCut + 1);

  const vals = [...obs, ...p16, ...p84, ...p50].filter((v) => Number.isFinite(v));
  const vmax = Math.max(...vals.map((v) => Math.log10(Math.max(v, 1e-9))));
  const vmin = Math.min(...vals.map((v) => Math.log10(Math.max(v, 1e-9))));

  const x = (l: number) =>
    SPECTRUM_PAD.left + ((l - 0) / Math.max(lCut, 1)) * (SPECTRUM_W - SPECTRUM_PAD.left - SPECTRUM_PAD.right);
  const y = (v: number) =>
    SPECTRUM_H -
    SPECTRUM_PAD.bottom -
    ((Math.log10(Math.max(v, 1e-9)) - vmin) / Math.max(vmax - vmin, 1e-9)) *
      (SPECTRUM_H - SPECTRUM_PAD.top - SPECTRUM_PAD.bottom);

  const line = (arr: number[]) => arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
  const bandPath = [
    `M${x(0)},${y(p16[0])}`,
    ...p84.map((_, i) => `L${x(i)},${y(p84[i])}`),
    ...[...p16].reverse().map((_, i) => `L${x(p16.length - 1 - i)},${y(p16[p16.length - 1 - i])}`),
    "Z",
  ].join(" ");

  return (
    <div>
      <svg width={SPECTRUM_W} height={SPECTRUM_H} className="spectrum-svg">
        <path d={bandPath} fill="#3fb950" opacity={0.12} />
        <path d={line(p50)} fill="none" stroke="#3fb950" strokeWidth={1} strokeDasharray="3 2" />
        <path d={line(obs)} fill="none" stroke="#58a6ff" strokeWidth={1.6} />
        {el.map((l) => (l % 8 === 0 || l === 0 ? (
          <text key={l} x={x(l)} y={SPECTRUM_H - 4} fontSize={8} fill="#8b949e" textAnchor="middle">
            {l}
          </text>
        ) : null))}
        <text x={4} y={10} fontSize={8} fill="#8b949e">
          log C_ℓ
        </text>
        <text x={SPECTRUM_W - 4} y={10} fontSize={8} fill="#8b949e" textAnchor="end">
          ℓ
        </text>
      </svg>
      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        blue = observed pseudo-C_ℓ · green = null median (uniform within footprint) with 16–84%
        band. Multipoles above the null band with small p-value deserve a physical reading.
      </p>
    </div>
  );
}

type ExcisionRow = {
  radius: string;
  n: number;
  mag: number;
  iso: number;
  kepler: number;
};

function ExcisionTable({ worlds }: { worlds: WorldAtlas }) {
  const rows: ExcisionRow[] = [
    {
      radius: "full",
      n: worlds.dipole.kepler_excision.n_worlds_full,
      mag: worlds.dipole.kepler_excision.full_magnitude,
      iso: worlds.dipole.kepler_excision.full_isotropic_expectation,
      kepler: worlds.dipole.references.kepler_field_center.separation_deg,
    },
    ...worlds.dipole.kepler_excision.rows.map((r) => ({
      radius: `>${r.radius_deg.toFixed(0)}°`,
      n: r.n_worlds,
      mag: r.magnitude,
      iso: r.isotropic_expectation,
      kepler: r.references.kepler_field_center.separation_deg,
    })),
  ];

  return (
    <div>
      <table className="world-method-table">
        <thead>
          <tr>
            <th>Cut</th>
            <th>N</th>
            <th>|dipole|</th>
            <th>iso exp</th>
            <th>↔ Kepler</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.radius}>
              <td>{r.radius}</td>
              <td>{r.n}</td>
              <td>{r.mag.toFixed(3)}</td>
              <td>{r.iso.toFixed(3)}</td>
              <td>{r.kepler.toFixed(0)}°</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted" style={{ marginTop: 8 }}>
        Removing the Kepler field collapses the dipole toward the isotropic expectation —
        the "scar" is the footprint, not physics.
      </p>
    </div>
  );
}

function CrossSkyTable({ report }: { report: CrossSkyReport }) {
  if (report.skies.length === 0) {
    return <p className="muted">No independent skies cached yet.</p>;
  }
  const refLabel = (refs: WorldDipoleRefs, key: keyof WorldDipoleRefs) =>
    refs[key] ? `${refs[key].separation_deg.toFixed(0)}°` : "—";
  return (
    <div>
      <table className="world-method-table">
        <thead>
          <tr>
            <th>Sky</th>
            <th>N</th>
            <th>|dipole|</th>
            <th>iso exp</th>
            <th>↔ CMB apex</th>
            <th>↔ Kepler</th>
          </tr>
        </thead>
        <tbody>
          {report.skies.map((s) => (
            <tr key={s.sky}>
              <td>{s.sky.replace(/_/g, " ")}</td>
              <td>{s.n_objects}</td>
              <td>{s.magnitude != null ? s.magnitude.toFixed(3) : "—"}</td>
              <td>{s.isotropic_expectation != null ? s.isotropic_expectation.toFixed(3) : "—"}</td>
              <td>{refLabel(s.references, "CMB_dipole_apex")}</td>
              <td>{refLabel(s.references, "kepler_field_center")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {report.pairwise.map((p) => (
        <p key={`${p.sky_a}-${p.sky_b}`} className={p.separation_deg < 30 ? "warn" : undefined}>
          {p.sky_a.replace(/_/g, " ")} ↔ {p.sky_b.replace(/_/g, " ")} dipole axes{" "}
          <strong>{p.separation_deg.toFixed(0)}°</strong> apart
          {p.separation_deg >= 30 && <span className="muted"> — no common axis</span>}
        </p>
      ))}
      <p className="muted" style={{ marginTop: 8 }}>
        Independent skies must agree on a preferred axis for a scar to be physical. Dipoles
        that point at each survey's own footprint are not physics.
      </p>
    </div>
  );
}

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
  const features: GeoJSON.Feature[] = [
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
  ];

  // World-dipole tip (only if CMB apex is beyond the 68% cone — otherwise the
  // dipole is just the survey footprint, and plotting it misleads).
  const dip = worlds.dipole;
  if (dip && dip.vector && dip.bootstrap) {
    const kepler = dip.references.kepler_field_center.separation_deg;
    const cone = dip.bootstrap.sigma68_deg;
    if (kepler > cone) {
      const v = dip.vector;
      const ra = Math.atan2(v[1], v[0]) * (180 / Math.PI);
      const dec = Math.asin(Math.max(-1, Math.min(1, v[2]))) * (180 / Math.PI);
      features.push({
        type: "Feature",
        properties: { kind: "world_dipole" },
        geometry: { type: "Point", coordinates: [(ra + 360) % 360, dec] },
      });
    }
  }

  return { type: "FeatureCollection", features };
}

export default function WorldAtlas({ height = 520 }: { height?: number }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [worlds, setWorlds] = useState<WorldAtlas | null>(null);
  const [crossSky, setCrossSky] = useState<CrossSkyReport | null>(null);
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
    let cancelled = false;
    api
      .cosmosCrossSky(20)
      .then((r) => {
        if (!cancelled) setCrossSky(r);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

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
      map.addLayer({
        id: "world-dipole-marker",
        type: "circle",
        source: "rble-overlays",
        filter: ["==", ["get", "kind"], "world_dipole"],
        paint: {
          "circle-radius": 7,
          "circle-color": "#a371f7",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
          "circle-opacity": 0.9,
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
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: "#a371f7" }} /> World dipole (if distinct)
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

          <div className="card cosmos-metrics">
            <h3>World dipole — cosmic-rest-frame test</h3>
            {worlds?.dipole && (
              <>
                <p>
                  |⟨n⟩| = <strong>{worlds.dipole.magnitude.toFixed(3)}</strong>{" "}
                  <span className="muted">(0 isotropic → 1 concentrated)</span>
                </p>
                <p>
                  68% cone <strong>{worlds.dipole.bootstrap.sigma68_deg.toFixed(1)}°</strong>
                  {worlds.dipole.bootstrap_per_host && (
                    <>
                      {" "}
                      <span className="muted">
                        (per-host {worlds.dipole.bootstrap_per_host.sigma68_deg.toFixed(1)}°,
                        {worlds.dipole.bootstrap_per_host.n_units} systems)
                      </span>
                    </>
                  )}
                </p>
                {Object.entries(worlds.dipole.references).map(([name, ref]) => {
                  const isKepler = name === "kepler_field_center";
                  const close =
                    ref.separation_deg < Math.max(worlds.dipole.bootstrap.sigma68_deg, 5);
                  return (
                    <p key={name} className={isKepler && close ? "warn" : undefined}>
                      ↔ {name.replace(/_/g, " ")}{" "}
                      <strong>{ref.separation_deg.toFixed(1)}°</strong>
                      {isKepler && close && (
                        <span className="muted"> — dipole is the survey footprint</span>
                      )}
                    </p>
                  );
                })}
                <p className="muted">
                  The CMB dipole apex is the Solar System's motion through the cosmic rest
                  frame — the one direction a <em>physical</em> anisotropy must point at.
                </p>
              </>
            )}
          </div>

          <div className="card cosmos-metrics">
            <h3>Kepler-excision scan</h3>
            {worlds?.dipole?.kepler_excision && <ExcisionTable worlds={worlds} />}
          </div>

          <div className="card cosmos-metrics">
            <h3>Cross-sky axis test</h3>
            {crossSky && <CrossSkyTable report={crossSky} />}
          </div>

          <BubbleSearchCard />

          <div className="card cosmos-metrics">
            <h3>World-sky power spectrum C_ℓ</h3>
            {worlds?.spectrum && (
              <WorldSpectrumChart spectrum={worlds.spectrum} />
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
