import Plot from "react-plotly.js";
import type { CosmosSky } from "../api/client";

type Props = {
  sky: CosmosSky;
  title: string;
  projection?: "orthographic" | "mollweide" | "equirectangular";
  rotationLon?: number;
  height?: number;
};

export function skyTraces(sky: CosmosSky) {
  return [
    {
      type: "scattergeo" as const,
      lon: sky.lon,
      lat: sky.lat,
      marker: {
        size: 2.5,
        color: sky.values,
        colorscale: "RdBu",
        cmin: -400,
        cmax: 400,
        opacity: 0.8,
        colorbar: { title: "µK", len: 0.45, y: 0.5 },
      },
      name: "CMB T",
    },
    {
      type: "scattergeo" as const,
      lon: sky.scar_ring.lon,
      lat: sky.scar_ring.lat,
      mode: "lines" as const,
      line: { color: "#ff7043", width: 2 },
      name: "Scar ring",
    },
    {
      type: "scattergeo" as const,
      lon: [sky.axis_marker.lon],
      lat: [sky.axis_marker.lat],
      mode: "markers" as const,
      marker: { size: 14, color: "#3fb950", symbol: "star" },
      name: "Axis",
    },
  ];
}

export default function CosmosSkyPlot({
  sky,
  title,
  projection = "orthographic",
  rotationLon = 30,
  height = 340,
}: Props) {
  return (
    <div className="sky-plot-wrap">
      <div className="sky-plot-title">
        {title}
        <span className="sky-score">S={sky.rble_score.toFixed(3)}</span>
      </div>
      <Plot
        data={skyTraces(sky)}
        layout={{
          paper_bgcolor: "#161b22",
          geo: {
            bgcolor: "#0d1117",
            projection: {
              type: projection,
              ...(projection === "orthographic"
                ? { rotation: { lon: rotationLon, lat: -20 } }
                : {}),
            },
            showland: false,
            showcountries: false,
            showocean: true,
            oceancolor: "#0d1117",
          },
          margin: { l: 0, r: 0, t: 0, b: 0 },
          height,
          showlegend: false,
        }}
        config={{ displayModeBar: false, scrollZoom: true }}
        style={{ width: "100%" }}
      />
    </div>
  );
}
