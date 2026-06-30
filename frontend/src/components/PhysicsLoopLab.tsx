import { useCallback, useState } from "react";
import Plot from "react-plotly.js";
import { api, PhysicsLoopPanel } from "../api/client";

const MAPS = ["wmap_k_band", "planck_smica_cmb"] as const;

export default function PhysicsLoopLab() {
  const [steps, setSteps] = useState(3);
  const [nside, setNside] = useState(32);
  const [mapProduct, setMapProduct] = useState<(typeof MAPS)[number]>("wmap_k_band");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PhysicsLoopPanel | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.physicsLoop({ steps, nside, mapProduct }));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [steps, nside, mapProduct]);

  const stepTrace = data?.steps?.length
    ? {
        x: data.steps.map((s) => s.step),
        y: data.steps.map((s) => s.separation_deg),
        type: "scatter" as const,
        mode: "lines+markers" as const,
        name: "sim vs real sky (°)",
        line: { color: "#3fb950" },
      }
    : null;

  const alignTrace = data?.steps?.length
    ? {
        x: data.steps.map((s) => s.step),
        y: data.steps.map((s) => s.alignment_quality),
        type: "scatter" as const,
        mode: "lines+markers" as const,
        name: "alignment |dot|",
        yaxis: "y2" as const,
        line: { color: "#d29922" },
      }
    : null;

  return (
    <section className="physics-loop-lab">
      <div className="section-label">Physics Loop — simulation adapted to real CMB axis</div>
      <div className="loop-controls">
        <label>
          Steps
          <input type="range" min={1} max={6} value={steps} onChange={(e) => setSteps(Number(e.target.value))} />
          {steps}
        </label>
        <label>
          NSIDE
          <input type="range" min={16} max={64} step={16} value={nside} onChange={(e) => setNside(Number(e.target.value))} />
          {nside}
        </label>
        <label>
          Map
          <select value={mapProduct} onChange={(e) => setMapProduct(e.target.value as typeof mapProduct)}>
            {MAPS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={run} disabled={loading}>
          {loading ? "Scanning real sky…" : "Run physics loop"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <p className="loop-summary">
          Real sky S_RBLE={data.real_score?.toFixed(4)} · axis=[
          {data.real_axis?.map((v) => v.toFixed(2)).join(", ")}] · final separation=
          {data.final_separation_deg?.toFixed(2)}°
        </p>
      )}
      <div className="grid">
        <div className="card">
          <h2>Sim ↔ real sky alignment</h2>
          {stepTrace && alignTrace && (
            <Plot
              data={[stepTrace, alignTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#0d1117",
                font: { color: "#e6edf3" },
                height: 260,
                margin: { l: 48, r: 48, t: 24, b: 40 },
                xaxis: { title: "step" },
                yaxis: { title: "separation (°)" },
                yaxis2: { title: "alignment", overlaying: "y", side: "right" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>
      </div>
    </section>
  );
}
