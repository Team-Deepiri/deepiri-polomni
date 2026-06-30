import { useCallback, useState } from "react";
import Plot from "react-plotly.js";
import { api, ClosedLoopPanel, DistrictGraphData } from "../api/client";

type Props = {
  onGraphUpdate?: (graph: DistrictGraphData) => void;
};

const POLICIES = ["uniform", "axis_biased", "entropy_max"] as const;

function downsampleTrace(values: number[], maxPoints = 2048): number[] {
  if (values.length <= maxPoints) return values;
  const step = Math.ceil(values.length / maxPoints);
  return values.filter((_, i) => i % step === 0);
}

export default function ClosedLoopLab({ onGraphUpdate }: Props) {
  const [steps, setSteps] = useState(3);
  const [choices, setChoices] = useState(4);
  const [nside, setNside] = useState(32);
  const [policy, setPolicy] = useState<(typeof POLICIES)[number]>("axis_biased");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ClosedLoopPanel | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const panel = await api.closedLoop({ steps, choices, nside, policy });
      setData(panel);
      onGraphUpdate?.(panel.graph);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [steps, choices, nside, policy, onGraphUpdate]);

  const stepTrace = data?.steps?.length
    ? {
        x: data.steps.map((s) => s.step),
        y: data.steps.map((s) => s.axis_error_deg),
        type: "scatter" as const,
        mode: "lines+markers" as const,
        name: "axis error (°)",
        line: { color: "#58a6ff" },
      }
    : null;

  const scoreTrace = data?.steps?.length
    ? {
        x: data.steps.map((s) => s.step),
        y: data.steps.map((s) => s.rble_score),
        type: "scatter" as const,
        mode: "lines+markers" as const,
        name: "S_RBLE",
        yaxis: "y2" as const,
        line: { color: "#ff7043" },
      }
    : null;

  const cmbValues = data?.cmb_values?.length ? downsampleTrace(data.cmb_values) : [];
  const cmbStep =
    data?.cmb_values?.length && cmbValues.length
      ? Math.ceil(data.cmb_values.length / cmbValues.length)
      : 1;
  const cmbLon = data?.cmb_lon?.filter((_, i) => i % cmbStep === 0) ?? [];
  const cmbLat = data?.cmb_lat?.filter((_, i) => i % cmbStep === 0) ?? [];
  const cmbTrace =
    cmbValues.length > 0 && cmbLon.length > 0
      ? {
          type: "scattergeo" as const,
          lon: cmbLon,
          lat: cmbLat,
          marker: {
            size: 3,
            color: cmbValues,
            colorscale: "RdBu",
            opacity: 0.7,
          },
        }
      : null;

  const graph = data?.graph;
  const edgeTraces =
    graph?.edges?.map((e) => {
      const src = graph.nodes.find((n) => n.id === e.source);
      const tgt = graph.nodes.find((n) => n.id === e.target);
      if (!src || !tgt) return null;
      return {
        type: "scatter3d" as const,
        mode: "lines" as const,
        x: [src.x, tgt.x],
        y: [src.y, tgt.y],
        z: [src.z, tgt.z],
        line: { width: 2 + e.conductance * 8, color: "#8b949e" },
        hoverinfo: "skip" as const,
        showlegend: false,
      };
    }).filter(Boolean) ?? [];

  const nodeTrace = graph
    ? {
        x: graph.nodes.map((n) => n.x),
        y: graph.nodes.map((n) => n.y),
        z: graph.nodes.map((n) => n.z),
        mode: "markers+text" as const,
        type: "scatter3d" as const,
        text: graph.nodes.map((n) => n.id),
        marker: { size: 5, color: graph.nodes.map((n) => n.mass) },
        name: "districts",
      }
    : null;

  return (
    <section className="closed-loop-lab">
      <div className="section-label">Closed RBLE Loop — sim → CMB → scan → feedback</div>
      <div className="loop-controls">
        <label>
          Steps
          <input
            type="range"
            min={1}
            max={6}
            value={steps}
            onChange={(e) => setSteps(Number(e.target.value))}
          />
          {steps}
        </label>
        <label>
          Choices
          <input
            type="range"
            min={2}
            max={8}
            value={choices}
            onChange={(e) => setChoices(Number(e.target.value))}
          />
          {choices}
        </label>
        <label>
          NSIDE
          <input
            type="range"
            min={16}
            max={64}
            step={16}
            value={nside}
            onChange={(e) => setNside(Number(e.target.value))}
          />
          {nside}
        </label>
        <label>
          Policy
          <select value={policy} onChange={(e) => setPolicy(e.target.value as typeof policy)}>
            {POLICIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={run} disabled={loading}>
          {loading ? "Running loop…" : "Run closed loop"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <p className="loop-summary">
          Final axis error: {data.final_axis_error_deg?.toFixed(2)}° · Graph:{" "}
          {data.graph.nodes.length} nodes · Last S_RBLE:{" "}
          {data.steps[data.steps.length - 1]?.rble_score.toFixed(4)}
        </p>
      )}
      <div className="grid">
        <div className="card">
          <h2>Loop convergence</h2>
          {stepTrace && scoreTrace && (
            <Plot
              data={[stepTrace, scoreTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#0d1117",
                font: { color: "#e6edf3" },
                height: 260,
                margin: { l: 48, r: 48, t: 24, b: 40 },
                xaxis: { title: "step" },
                yaxis: { title: "axis error (°)" },
                yaxis2: { title: "S_RBLE", overlaying: "y", side: "right" },
                showlegend: true,
                legend: { orientation: "h" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>
        <div className="card">
          <h2>Imprinted CMB (last step)</h2>
          {cmbTrace && (
            <Plot
              data={[cmbTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                geo: { bgcolor: "#161b22", projection: { type: "orthographic" } },
                margin: { l: 0, r: 0, t: 0, b: 0 },
                height: 260,
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>
        <div className="card">
          <h2>District graph (post-loop)</h2>
          {nodeTrace && (
            <Plot
              data={[...(edgeTraces as object[]), nodeTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#161b22",
                font: { color: "#e6edf3" },
                height: 280,
                margin: { l: 0, r: 0, t: 0, b: 0 },
                scene: { bgcolor: "#161b22" },
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
