import { useCallback, useEffect, useRef, useState } from "react";
import Plot from "react-plotly.js";
import {
  api,
  type CosmosSnapshot,
  type ProgressEvent,
} from "../api/client";
import SkyMapLibre from "./SkyMapLibre";
import AladinSkyViewer from "./AladinSkyViewer";

const plotLayout = {
  paper_bgcolor: "#161b22",
  plot_bgcolor: "#0d1117",
  font: { color: "#e6edf3" },
  margin: { l: 48, r: 16, t: 24, b: 40 },
};

function Lamp({ ok }: { ok: boolean }) {
  return <span className={`lamp ${ok ? "ok" : "fail"}`} />;
}

export default function CosmosLab() {
  const [compare, setCompare] = useState<any>(null);
  const [power, setPower] = useState<any>(null);
  const [nullTiers, setNullTiers] = useState<any>(null);
  const [histogram, setHistogram] = useState<any>(null);
  const [study, setStudy] = useState<any>(null);
  const [proofs, setProofs] = useState<any[]>([]);
  const [snapshot, setSnapshot] = useState<CosmosSnapshot | null>(null);
  const [verifyRunning, setVerifyRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastTick, setLastTick] = useState("");
  const [autoRotate, setAutoRotate] = useState(true);
  const progressRef = useRef<EventSource | null>(null);

  const loadCosmos = useCallback(async () => {
    try {
      setError(null);
      const [cmp, ps, nt, hist, st] = await Promise.all([
        api.cosmosCompare(64),
        api.cosmosPowerSpectrum(),
        api.cosmosNullTiers(64, "planck_smica_cmb"),
        api.cosmosHistogram("planck_smica_cmb", 64),
        api.cosmosStudy(),
      ]);
      setCompare(cmp);
      setPower(ps);
      setNullTiers(nt);
      setHistogram(hist);
      setStudy(st);
      const studyData = st as { proofs?: { results?: unknown[] } };
      setProofs((studyData.proofs?.results ?? []) as any[]);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    loadCosmos();
  }, [loadCosmos]);

  useEffect(() => {
    const es = new EventSource("/cosmos/live?interval=6&ticks=9999");
    es.onmessage = (ev) => {
      try {
        const snap = JSON.parse(ev.data) as CosmosSnapshot;
        setSnapshot(snap);
        setLastTick(snap.timestamp);
        if (typeof snap.verify_running === "boolean") setVerifyRunning(snap.verify_running);
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, []);

  const startVerify = async (blind: boolean) => {
    setVerifyRunning(true);
    setProgress([]);
    progressRef.current?.close();
    const es = new EventSource("/cosmos/verify/progress?interval=0.8&ticks=9999");
    progressRef.current = es;
    es.onmessage = (ev) => {
      try {
        const evn = JSON.parse(ev.data) as ProgressEvent;
        if (evn.step === "idle") {
          es.close();
          return;
        }
        setProgress((prev) => [...prev, evn]);
      } catch {
        /* ignore */
      }
    };
    await api.cosmosVerify(blind);
    const poll = setInterval(async () => {
      const st = await api.cosmosVerifyStatus();
      setVerifyRunning(st.running);
      if (!st.running) {
        clearInterval(poll);
        es.close();
        await loadCosmos();
      }
    }, 3000);
  };

  useEffect(() => () => progressRef.current?.close(), []);

  const gates = snapshot?.gates ?? study?.gates;
  const result = snapshot?.study ?? study?.result ?? compare?.study_result;
  const calSky = compare?.calibration?.sky ?? null;
  const holdSky = compare?.holdout?.sky ?? null;
  const calProfile = compare?.calibration?.axis_profile;
  const holdProfile = compare?.holdout?.axis_profile;
  const verdict = compare?.verdict;

  return (
    <section className="cosmos-lab">
      <div className="cosmos-header">
        <div>
          <h2>Cosmos Lab — Real Data Observatory</h2>
          <p className="cosmos-sub">
            WMAP calibration vs Planck blind holdout · live verification · null ensembles
            {verdict && (
              <>
                {" "}
                · ΔS={verdict.score_delta?.toFixed(2)}
                {verdict.p1_falsified && (
                  <span className="fail-text"> · P1 falsified on holdout</span>
                )}
              </>
            )}
          </p>
        </div>
        <div className="cosmos-actions">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={autoRotate}
              onChange={(e) => setAutoRotate(e.target.checked)}
            />
            Spin globe
          </label>
          <button disabled={verifyRunning} onClick={() => startVerify(false)}>
            {verifyRunning ? "Running…" : "Full Verification"}
          </button>
          <button className="btn-warn" disabled={verifyRunning} onClick={() => startVerify(true)}>
            Blind Holdout
          </button>
          <button onClick={loadCosmos}>Refresh</button>
        </div>
      </div>

      {error && <p className="error cosmos-error">{error}</p>}
      {lastTick && (
        <p className="live-pulse">
          <span className="pulse-dot" /> Live · {new Date(lastTick).toLocaleTimeString()}
        </p>
      )}

      <div className="cosmos-grid-v2">
        <div className="card cosmos-dual cosmos-sky-hero">
          <AladinSkyViewer
            mapProduct="wmap_k_band"
            nside={64}
            height={520}
            title="Live Cosmos Observatory — real telescope & satellite surveys"
          />
        </div>

        <div className="card cosmos-dual">
          <h3>Calibration vs Holdout — CMB microwave globes</h3>
          <div className="dual-sky-row">
            <SkyMapLibre
              mapProduct="wmap_k_band"
              nside={64}
              height={320}
              title="WMAP Ka calibration"
              autoRotate={autoRotate}
              showControls={false}
            />
            <SkyMapLibre
              mapProduct="planck_smica_cmb"
              nside={64}
              height={320}
              title="Planck SMICA holdout"
              autoRotate={autoRotate}
              showControls={false}
            />
          </div>
          {verdict && (
            <div className="verdict-bar">
              <div className="verdict-item">
                <span>WMAP S_RBLE</span>
                <strong>{calSky?.rble_score.toFixed(3)}</strong>
              </div>
              <div className="verdict-item">
                <span>Planck S_RBLE</span>
                <strong>{holdSky?.rble_score.toFixed(3)}</strong>
              </div>
              <div className="verdict-item">
                <span>Holdout</span>
                <strong className={verdict.p1_falsified ? "fail-text" : "ok-text"}>
                  {verdict.p1_supported ? "SUPPORTED" : "FALSIFIED"}
                </strong>
              </div>
            </div>
          )}
        </div>

        <div className="cosmos-side">
          <div className="card cosmos-metrics">
            <h3>Status</h3>
            <p>
              <Lamp ok={gates?.all_passed ?? false} /> Gates {gates?.passed ?? 0}/
              {gates?.checks?.length ?? 3}
            </p>
            <p>
              <Lamp ok={snapshot?.proofs_all_passed ?? false} /> Proofs{" "}
              {snapshot?.proofs_passed ?? proofs.filter((p) => p.passed).length}/
              {snapshot?.proofs_total ?? proofs.length}
            </p>
            <p>
              <Lamp ok={!!result?.p1_supported} /> Study: {result?.mode ?? "—"}
            </p>
            {result?.detection && (
              <div className="study-detail">
                <div>S_RBLE = {Number(result.detection.rble_score).toFixed(4)}</div>
              </div>
            )}
          </div>

          <div className="card progress-log">
            <h3>Verification Log</h3>
            <div className="log-scroll">
              {progress.length === 0 && (
                <p className="muted">Run verification to stream live steps…</p>
              )}
              {progress.map((p, i) => (
                <div key={`${p.step}-${i}`} className={`log-line log-${p.step}`}>
                  <span className="log-time">
                    {new Date(p.timestamp).toLocaleTimeString()}
                  </span>{" "}
                  {p.message}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Null Score Distribution (Planck holdout)</h3>
          {histogram?.histogram && (
            <Plot
              data={[
                {
                  x: histogram.histogram.bin_centers,
                  y: histogram.histogram.counts,
                  type: "bar",
                  marker: { color: "#58a6ff" },
                  name: "Null ensemble",
                },
                {
                  x: [histogram.observed_score, histogram.observed_score],
                  y: [0, Math.max(...histogram.histogram.counts) * 1.1],
                  type: "scatter",
                  mode: "lines",
                  line: { color: "#f85149", width: 3, dash: "dash" },
                  name: "Observed",
                },
              ]}
              layout={{
                ...plotLayout,
                height: 260,
                xaxis: { title: "S_RBLE", gridcolor: "#30363d" },
                yaxis: { title: "Count", gridcolor: "#30363d" },
                showlegend: true,
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
          {histogram && (
            <p className="muted">
              μ_null={histogram.null_mu?.toFixed(3)} σ={histogram.raw_sigma?.toFixed(2)} · n=
              {histogram.n_ensemble}
            </p>
          )}
        </div>

        <div className="card">
          <h3>Axis Radial Profile |T| vs θ from scar axis</h3>
          {calProfile && holdProfile && (
            <Plot
              data={[
                {
                  x: calProfile.angle_deg,
                  y: calProfile.mean_abs_t,
                  type: "scatter",
                  mode: "lines+markers",
                  line: { color: "#58a6ff" },
                  name: "WMAP",
                },
                {
                  x: holdProfile.angle_deg,
                  y: holdProfile.mean_abs_t,
                  type: "scatter",
                  mode: "lines+markers",
                  line: { color: "#ff7043" },
                  name: "Planck",
                },
              ]}
              layout={{
                ...plotLayout,
                height: 260,
                xaxis: { title: "Angle from axis [deg]", gridcolor: "#30363d" },
                yaxis: { title: "Mean |T|", gridcolor: "#30363d" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>

        <div className="card">
          <h3>Planck TT + CAMB ΛCDM Theory</h3>
          {power?.ell?.length > 0 && (
            <Plot
              data={[
                {
                  x: power.ell,
                  y: power.dl,
                  type: "scatter",
                  mode: "lines",
                  line: { color: "#58a6ff" },
                  name: "Planck TT",
                },
                ...(power.camb_theory
                  ? [
                      {
                        x: power.ell,
                        y: power.camb_theory,
                        type: "scatter",
                        mode: "lines",
                        line: { color: "#d29922", dash: "dot" },
                        name: "CAMB ΛCDM",
                      },
                    ]
                  : []),
              ]}
              layout={{
                ...plotLayout,
                height: 240,
                xaxis: { title: "ℓ", gridcolor: "#30363d" },
                yaxis: { title: "D_ℓ [µK²]", gridcolor: "#30363d", type: "log" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>

        <div className="card">
          <h3>Null Tiers (Planck holdout map)</h3>
          {nullTiers?.chart && (
            <Plot
              data={[
                {
                  x: nullTiers.chart.labels,
                  y: nullTiers.chart.raw_sigma,
                  type: "bar",
                  marker: {
                    color: nullTiers.chart.p_values.map((p: number) =>
                      p < 0.05 ? "#3fb950" : "#8b949e",
                    ),
                  },
                  name: "σ_raw",
                },
              ]}
              layout={{
                ...plotLayout,
                height: 240,
                yaxis: { title: "σ vs null tier", gridcolor: "#30363d" },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          )}
        </div>

        <div className="card proof-panel">
          <h3>Math Proof Suite ({proofs.filter((p) => p.passed).length}/{proofs.length})</h3>
          <div className="proof-scroll">
            {proofs.map((p: any) => (
              <div key={p.id} className={p.passed ? "proof-ok" : "proof-fail"}>
                {p.passed ? "✓" : "✗"} <code>{p.id}</code> — {p.message?.slice(0, 72)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
