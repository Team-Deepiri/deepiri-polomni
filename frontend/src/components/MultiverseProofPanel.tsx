import { useCallback, useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { api, DistrictGraphData } from '../api/client';

type ProofMetric = {
  id: string;
  name: string;
  passed: boolean;
  value: number;
  threshold: number;
  unit: string;
  message: string;
};

type MultiverseProofPayload = {
  proof: {
    all_passed: boolean;
    pass_rate: number;
    mode: string;
    elapsed_seconds: number;
    metrics: ProofMetric[];
    p1_gates?: { all_passed: boolean; passed: number };
  };
  loop_series: {
    step: number[];
    axis_error_deg: number[];
    rble_score: number[];
  };
  multiverse_graph: DistrictGraphData;
  branch_depth: number[];
  evidence_tier: string;
};

export default function MultiverseProofPanel() {
  const [data, setData] = useState<MultiverseProofPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/viz/multiverse-proof?quick=true');
      if (!res.ok) throw new Error(`${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const graph = data?.multiverse_graph;
  const nodeTrace = graph
    ? {
        x: graph.nodes.map((n) => n.x),
        y: graph.nodes.map((n) => n.y),
        z: graph.nodes.map((n) => n.z),
        mode: 'markers+text' as const,
        type: 'scatter3d' as const,
        text: graph.nodes.map((n) => n.id),
        marker: { size: 6, color: graph.nodes.map((n) => n.mass), colorscale: 'Plasma' },
        name: 'districts',
      }
    : null;

  const edgeTraces =
    graph?.edges?.map((e) => {
      const src = graph.nodes.find((n) => n.id === e.source);
      const tgt = graph.nodes.find((n) => n.id === e.target);
      if (!src || !tgt) return null;
      return {
        type: 'scatter3d' as const,
        mode: 'lines' as const,
        x: [src.x, tgt.x],
        y: [src.y, tgt.y],
        z: [src.z, tgt.z],
        line: { width: 2 + e.conductance * 10, color: '#58a6ff' },
        showlegend: false,
        hoverinfo: 'skip' as const,
      };
    }).filter(Boolean) ?? [];

  const loopTrace = data?.loop_series
    ? {
        x: data.loop_series.step,
        y: data.loop_series.axis_error_deg,
        type: 'scatter' as const,
        mode: 'lines+markers' as const,
        name: 'axis error (°)',
        line: { color: '#3fb950' },
      }
    : null;

  const branchTrace = data?.branch_depth?.length
    ? {
        x: data.branch_depth.map((_, i) => i),
        y: data.branch_depth,
        type: 'bar' as const,
        marker: { color: '#ff7043' },
        name: 'branches per depth',
      }
    : null;

  return (
    <section className="multiverse-proof">
      <div className="section-label">
        Multiverse Computational Proof — injection · loop · branching · real-sky bridge
      </div>
      <div className="loop-controls">
        <button type="button" onClick={load} disabled={loading}>
          {loading ? 'Running proof…' : 'Refresh proof'}
        </button>
        {data && (
          <span className="loop-summary">
            Tier: {data.evidence_tier.replace(/_/g, ' ')} · {Math.round(data.proof.pass_rate * 100)}% pass ·{' '}
            {data.proof.elapsed_seconds.toFixed(1)}s
          </span>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        <div className="card">
          <h2>Proof metrics</h2>
          <div style={{ fontSize: 13, maxHeight: 280, overflow: 'auto' }}>
            {data?.proof.metrics.map((m) => (
              <p key={m.id}>
                <span className={`lamp ${m.passed ? 'ok' : 'fail'}`} />
                {m.name}: {m.message}
              </p>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>Loop convergence</h2>
          {loopTrace && (
            <Plot
              data={[loopTrace]}
              layout={{
                paper_bgcolor: '#161b22',
                plot_bgcolor: '#0d1117',
                font: { color: '#e6edf3' },
                height: 260,
                margin: { l: 48, r: 16, t: 24, b: 40 },
                yaxis: { title: 'axis error (°)' },
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%' }}
            />
          )}
        </div>
        <div className="card">
          <h2>Multiverse branching depth</h2>
          {branchTrace && (
            <Plot
              data={[branchTrace]}
              layout={{
                paper_bgcolor: '#161b22',
                plot_bgcolor: '#0d1117',
                font: { color: '#e6edf3' },
                height: 260,
                margin: { l: 48, r: 16, t: 24, b: 40 },
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%' }}
            />
          )}
        </div>
        <div className="card">
          <h2>Multiverse district graph (4-depth chain)</h2>
          {nodeTrace && (
            <Plot
              data={[...(edgeTraces as object[]), nodeTrace]}
              layout={{
                paper_bgcolor: '#161b22',
                scene: {
                  bgcolor: '#161b22',
                  xaxis: { title: 'x' },
                  yaxis: { title: 'y' },
                  zaxis: { title: 'z' },
                },
                height: 300,
                margin: { l: 0, r: 0, t: 0, b: 0 },
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%' }}
            />
          )}
        </div>
      </div>
    </section>
  );
}
