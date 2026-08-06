import { useCallback, useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api, DistrictGraphData } from "./api/client";
import CosmosLab from "./components/CosmosLab";
import ClosedLoopLab from "./components/ClosedLoopLab";
import MultiverseProofPanel from "./components/MultiverseProofPanel";
import PhysicsLoopLab from "./components/PhysicsLoopLab";
import RadonTomography from "./components/RadonTomography";
import SkyMapLibre from "./components/SkyMapLibre";
import AladinSkyViewer from "./components/AladinSkyViewer";
import WorldAtlas from "./components/WorldAtlas";

type PanelProps = { title: string; children: React.ReactNode };

function Panel({ title, children }: PanelProps) {
  return (
    <div className="card">
      <h2>{title}</h2>
      {children}
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState("…");
  const [error, setError] = useState<string | null>(null);
  const [district, setDistrict] = useState<DistrictGraphData | null>(null);
  const [landscape, setLandscape] = useState<any>(null);
  const [scar, setScar] = useState<any>(null);
  const [stream, setStream] = useState<any>(null);
  const [branch, setBranch] = useState<any>(null);
  const [fals, setFals] = useState<any>(null);
  const [proofs, setProofs] = useState<any[]>([]);

  const load = useCallback(async () => {
    try {
      setError(null);
      const h = await api.health();
      setHealth(h.status);
      const [dg, ls, sc, st, br, fa, pr] = await Promise.all([
        api.districtGraph(),
        api.landscape(),
        api.scarSphere(64, false),
        api.streamFlux(),
        api.branchSimplex(),
        api.falsification(),
        api.proofs(),
      ]);
      setDistrict(dg);
      setLandscape(ls);
      setScar(sc);
      setStream(st);
      setBranch(br);
      setFals(fa);
      setProofs(pr.results ?? []);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runProofs = async () => {
    const r = await api.prove();
    setProofs(r.results ?? []);
    await load();
  };

  const districtTrace = district
    ? {
        x: district.nodes.map((n: any) => n.x),
        y: district.nodes.map((n: any) => n.y),
        z: district.nodes.map((n: any) => n.z),
        mode: "markers+text" as const,
        type: "scatter3d" as const,
        text: district.nodes.map((n: any) => n.id),
        marker: { size: 6, color: district.nodes.map((n: any) => n.mass) },
      }
    : null;

  const landscapeTrace = landscape
    ? {
        x: landscape.x,
        y: landscape.y,
        z: landscape.z,
        type: "surface" as const,
        colorscale: "Viridis",
      }
    : null;

  return (
    <>
      <header>
        <h1>Polomni Observatory</h1>
        <div>
          <span style={{ marginRight: 12 }}>API: {health}</span>
          <button onClick={runProofs}>Run Proofs</button>
          <button onClick={load} style={{ marginLeft: 8 }}>
            Refresh
          </button>
        </div>
      </header>
      {error && <p className="error" style={{ padding: "0 1.5rem" }}>{error}</p>}

      <MultiverseProofPanel />
      <CosmosLab />
      <WorldAtlas />
      <ClosedLoopLab onGraphUpdate={setDistrict} />
      <PhysicsLoopLab />
      <RadonTomography />

      <div className="section-label">Multiverse Engine — Real Cosmos (Aladin HiPS)</div>
      <div className="multiverse-sky-wrap">
        <AladinSkyViewer
          mapProduct="wmap_k_band"
          nside={64}
          height={500}
          title="RBLE multiverse on real sky surveys"
        />
        {scar && (
          <p className="multiverse-sky-meta">
            S_RBLE={scar.rble_score?.toFixed(4)} · axis=[
            {scar.preferred_axis?.map((v: number) => v.toFixed(2)).join(", ")}]
          </p>
        )}
      </div>

      <div className="section-label">Multiverse Engine (synthetic)</div>
      <div className="grid">
        <Panel title="3D District Multiverse Graph">
          {districtTrace && (
            <Plot
              data={[districtTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#161b22",
                font: { color: "#e6edf3" },
                margin: { l: 0, r: 0, t: 0, b: 0 },
                height: 260,
                scene: { bgcolor: "#161b22" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </Panel>
        <Panel title="Kähler Landscape K_total">
          {landscapeTrace && (
            <Plot
              data={[landscapeTrace]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#161b22",
                font: { color: "#e6edf3" },
                margin: { l: 0, r: 0, t: 0, b: 0 },
                height: 260,
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </Panel>
        <Panel title="Stream Horizon Flux">
          {stream?.stages && (
            <Plot
              data={[
                {
                  x: stream.stages.map((s: any) => s.stage),
                  y: stream.stages.map((s: any) => s.flux),
                  type: "scatter",
                  mode: "lines+markers",
                  line: { color: "#58a6ff" },
                },
              ]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#0d1117",
                font: { color: "#e6edf3" },
                height: 240,
                margin: { l: 40, r: 10, t: 10, b: 40 },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </Panel>
        <Panel title="Branch Choice Simplex">
          {branch && (
            <Plot
              data={[
                {
                  x: branch.labels,
                  y: branch.weights,
                  type: "bar",
                  marker: { color: "#ff7043" },
                },
              ]}
              layout={{
                paper_bgcolor: "#161b22",
                plot_bgcolor: "#0d1117",
                font: { color: "#e6edf3" },
                height: 240,
                margin: { l: 40, r: 10, t: 10, b: 40 },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </Panel>
        <Panel title="Falsification P1–P3">
          {fals && (
            <div style={{ fontSize: 14 }}>
              <p>
                <span className={`lamp ${fals.p1 ? "ok" : "fail"}`} />
                P1 CMB scar
              </p>
              <p>
                <span className={`lamp ${fals.p2 ? "ok" : "fail"}`} />
                P2 directed diffusion
              </p>
              <p>
                <span className={`lamp ${fals.p3 ? "ok" : "fail"}`} />
                P3 GW conductance
              </p>
              <p style={{ color: "#8b949e" }}>
                Proofs all passed: {fals.proofs_all_passed ? "yes" : "no"}
              </p>
            </div>
          )}
        </Panel>
        <Panel title="Math Proof Suite">
          <div style={{ fontSize: 12, maxHeight: 220, overflow: "auto" }}>
            {proofs.map((p: any) => (
              <div key={p.id}>
                {p.passed ? "✓" : "✗"} {p.id}: {p.message?.slice(0, 40)}
              </div>
            ))}
            {proofs.length === 0 && <p style={{ color: "#8b949e" }}>Click Run Proofs</p>}
          </div>
        </Panel>
      </div>
    </>
  );
}
