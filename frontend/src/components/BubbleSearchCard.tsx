import { useEffect, useState } from "react";
import { api, type BubbleSearchReport } from "../api/client";

const PROFILE_W = 260;
const PROFILE_H = 110;
const PAD = { top: 10, right: 8, bottom: 18, left: 34 };

function RadialProfileChart({ report }: { report: BubbleSearchReport }) {
  const rows = report.strongest_circle.radial_profile.filter((r) => r.n_pixels > 0);
  if (rows.length < 2) return null;
  const rMax = Math.max(...rows.map((r) => r.radius_deg));
  const ts = rows.map((r) => r.mean_t_uk);
  const tMin = Math.min(...ts);
  const tMax = Math.max(...ts);

  const x = (r: number) =>
    PAD.left + (r / rMax) * (PROFILE_W - PAD.left - PAD.right);
  const y = (t: number) =>
    PROFILE_H - PAD.bottom - ((t - tMin) / Math.max(tMax - tMin, 1e-9)) * (PROFILE_H - PAD.top - PAD.bottom);

  const path = rows.map((r, i) => `${i === 0 ? "M" : "L"}${x(r.radius_deg)},${y(r.mean_t_uk)}`).join(" ");
  return (
    <div>
      <svg width={PROFILE_W} height={PROFILE_H} className="spectrum-svg">
        <path d={path} fill="none" stroke="#58a6ff" strokeWidth={1.6} />
        <text x={4} y={10} fontSize={8} fill="#8b949e">mean T (µK)</text>
        <text x={PROFILE_W - 4} y={PROFILE_H - 4} fontSize={8} fill="#8b949e" textAnchor="end">
          radius (°)
        </text>
      </svg>
      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        A bubble collision is a <strong>step</strong>: flat inside, flat outside, one sharp
        edge. A smooth gradient is large-scale CMB structure, not a bubble.
      </p>
    </div>
  );
}

export default function BubbleSearchCard() {
  const [report, setReport] = useState<BubbleSearchReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .cosmosBubbleSearch(128, 16)
      .then((r) => {
        if (!cancelled) setReport(r);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="card cosmos-metrics"><p className="warn">{error}</p></div>;
  if (!report) return <div className="card cosmos-metrics"><p className="muted">Loading bubble-collision search…</p></div>;

  const edge = report.null.max_abs_edge_uk;
  const sc = report.strongest_circle;
  const ha = report.harmonic_axis;
  return (
    <div className="card cosmos-metrics">
      <h3>Bubble-collision search — eternal inflation</h3>
      <p>
        Circles scanned <strong>{report.n_circles_scanned}</strong>
        <span className="muted"> · {report.map_product_id} · f_sky {report.mask.f_sky.toFixed(2)}</span>
      </p>
      <p>
        Strongest edge <strong>{edge.observed.toFixed(1)} µK</strong> vs null median{" "}
        <strong>{edge.median.toFixed(1)} µK</strong> →{" "}
        <strong>p = {report.p_value.toFixed(3)}</strong>
        <span className={report.p_value < 0.05 ? "warn" : "muted"}>
          {" "}
          {report.p_value < 0.05 ? " — candidate, needs checks" : " — consistent with null"}
        </span>
      </p>
      {sc.gal_lon != null && sc.gal_lat != null && sc.radius_deg != null && (
        <p>
          Strongest circle @ ({sc.gal_lon.toFixed(1)}°, {sc.gal_lat.toFixed(1)}°) gal, r={sc.radius_deg}°
        </p>
      )}
      <RadialProfileChart report={report} />
      {ha && (
        <div style={{ marginTop: 10, borderTop: "1px solid var(--border, #30363d)", paddingTop: 8 }}>
          <p>
            <strong>Rank-1 axis search</strong> — best axis ({ha.axis.gal_lon.toFixed(1)}°,{" "}
            {ha.axis.gal_lat.toFixed(1)}°) gal, score {ha.score.toFixed(3)} vs null max median{" "}
            {ha.null.max_score_median.toFixed(3)} → <strong>p = {ha.p_value.toFixed(3)}</strong>
            <span className={ha.p_value < 0.05 ? "warn" : "muted"}>
              {" "}
              {ha.p_value < 0.05 ? " — candidate, needs checks" : " — consistent with null"}
            </span>
          </p>
          <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
            Rank-1 invariant: a collision about n̂<sub>c</sub> has a_lm = C_l·Y_lm(n̂<sub>c</sub>) at every
            l, so its m=0 power fraction at the axis is 1 per multipole (isotropic: 1/(2l+1)). The CMB's
            own "axis of evil" alignment is absorbed into the null, not reported as a detection.
          </p>
        </div>
      )}
      <p className="muted" style={{ fontSize: 11, marginTop: 6 }}>
        {report.verdict}
      </p>
    </div>
  );
}
