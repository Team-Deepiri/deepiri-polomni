import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api } from "../api/client";

const layout = {
  paper_bgcolor: "#161b22",
  plot_bgcolor: "#0d1117",
  font: { color: "#e6edf3" },
  margin: { l: 52, r: 52, t: 28, b: 44 },
};

export default function RadonTomography() {
  const [tomogram, setTomogram] = useState<any>(null);
  const [landscape, setLandscape] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.cosmosTomogram("wmap_k_band", 64),
      api.cosmosLandscape("wmap_k_band", 64),
    ])
      .then(([tom, land]) => {
        setTomogram(tom);
        setLandscape(land);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="error cosmos-error">{error}</p>;

  const tom = tomogram?.tomogram;
  const etaDeg = tom?.eta?.map((r: number) => (r * 180) / Math.PI);

  return (
    <section className="radon-tomo card">
      <h3>Geodesic Radon Tomography — Eq. 6</h3>
      <p className="cosmos-sub mono-eq">
        {tomogram?.equation ?? "S_RBLE(n̂) = ∫ |R_S²[T⊗W_string](n̂,η)| dη"}
      </p>

      <div className="tomo-grid">
        {tom && (
          <div>
            <h4>Tomogram R(η) + bifurcation |R''|</h4>
            <Plot
              data={[
                {
                  x: etaDeg,
                  y: tom.profile,
                  type: "scatter",
                  mode: "lines",
                  name: "R_S²(η)",
                  line: { color: "#58a6ff", width: 2 },
                },
                {
                  x: etaDeg,
                  y: tom.bifurcation,
                  type: "scatter",
                  mode: "lines",
                  name: "|R''(η)|",
                  yaxis: "y2",
                  line: { color: "#ff7043", width: 1.5 },
                },
                ...(tom.te_conductance
                  ? [
                      {
                        x: etaDeg?.slice(0, tom.te_conductance.length),
                        y: tom.te_conductance,
                        type: "scatter",
                        mode: "lines",
                        name: "M(η) T–E",
                        line: { color: "#3fb950", dash: "dot" },
                      },
                    ]
                  : []),
              ]}
              layout={{
                ...layout,
                height: 300,
                xaxis: { title: "η [deg]", gridcolor: "#30363d" },
                yaxis: { title: "R geodesic integral", gridcolor: "#30363d" },
                yaxis2: {
                  title: "Bifurcation",
                  overlaying: "y",
                  side: "right",
                  gridcolor: "#30363d",
                },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
            <div className="metric-row">
              <span>S = {tom.score_integral?.toFixed(4)}</span>
              <span>Bif = {tom.score_bifurcation?.toFixed(6)}</span>
              <span>Contrast = {tom.score_contrast?.toFixed(3)}</span>
            </div>
            {tomogram?.fingerprint?.length > 0 && (
              <div className="fingerprint">
                <strong>Bifurcation fingerprint:</strong>{" "}
                {tomogram.fingerprint
                  .slice(0, 3)
                  .map((p: any) => `η=${p.eta_deg.toFixed(0)}° A=${p.amplitude.toExponential(2)}`)
                  .join(" · ")}
              </div>
            )}
          </div>
        )}

        {landscape && (
          <div>
            <h4>RBLE Axis Landscape on S² (novel scar field)</h4>
            <Plot
              data={[
                {
                  type: "scattergeo",
                  lon: landscape.lon,
                  lat: landscape.lat,
                  marker: {
                    size: 8,
                    color: landscape.scores,
                    colorscale: "Hot",
                    colorbar: { title: "S_RBLE", len: 0.6 },
                  },
                },
              ]}
              layout={{
                paper_bgcolor: "#161b22",
                geo: {
                  bgcolor: "#0d1117",
                  projection: { type: "mollweide" },
                  showland: false,
                  showcountries: false,
                },
                height: 300,
                margin: { l: 0, r: 0, t: 0, b: 0 },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
            <div className="metric-row">
              <span>Peak S = {landscape.peak_score?.toFixed(4)}</span>
              <span>μ = {landscape.score_mean?.toFixed(6)}</span>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
