import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "../api/client";

export type SkyMapProduct = "wmap_k_band" | "planck_smica_cmb";

type Props = {
  mapProduct?: SkyMapProduct;
  nside?: number;
  height?: number;
  title?: string;
  autoRotate?: boolean;
  showControls?: boolean;
  className?: string;
};

type OverlayMeta = {
  rble_score?: number;
  null_sigma?: number;
  map_product_id?: string;
};

const EMPTY_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#0d1117" } }],
};

function rasterUrl(product: string, nside: number) {
  return `/cosmos/sky/raster?map_product=${product}&nside=${nside}&width=1536&height=768`;
}

export default function SkyMapLibre({
  mapProduct = "wmap_k_band",
  nside = 64,
  height = 420,
  title = "Real CMB Sky",
  autoRotate = true,
  showControls = true,
  className = "",
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const spinRef = useRef<number | null>(null);
  const [meta, setMeta] = useState<OverlayMeta>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [product, setProduct] = useState(mapProduct);
  const [spinning, setSpinning] = useState(autoRotate);

  useEffect(() => {
    setProduct(mapProduct);
  }, [mapProduct]);

  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: EMPTY_STYLE,
      center: [30, -20],
      zoom: 0.65,
      maxZoom: 4,
      minZoom: 0.2,
      attributionControl: false,
      projection: { type: "globe" },
    } as maplibregl.MapOptions);
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

    const loadSky = async () => {
      setLoading(true);
      setError(null);
      try {
        await api.health();
        const overlays = await fetchJson<{
          type: string;
          features: unknown[];
          metadata?: OverlayMeta;
        }>(`/cosmos/sky/overlays?map_product=${product}&nside=${nside}`);
        if (cancelled) return;
        setMeta(overlays.metadata ?? {});

        const onReady = () => {
          if (cancelled) return;
          if (map.getSource("cmb-sky")) {
            map.removeLayer("cmb-sky-layer");
            map.removeSource("cmb-sky");
          }
          if (map.getSource("rble-overlays")) {
            map.removeLayer("axis-marker");
            map.removeLayer("scar-ring");
            map.removeSource("rble-overlays");
          }

          map.addSource("cmb-sky", {
            type: "image",
            url: rasterUrl(product, nside),
            coordinates: [
              [-180, 90],
              [180, 90],
              [180, -90],
              [-180, -90],
            ],
          });
          map.addLayer({
            id: "cmb-sky-layer",
            type: "raster",
            source: "cmb-sky",
            paint: { "raster-fade-duration": 0, "raster-opacity": 1 },
          });

          map.addSource("rble-overlays", {
            type: "geojson",
            data: overlays as unknown as GeoJSON.FeatureCollection,
          });
          map.addLayer({
            id: "scar-ring",
            type: "line",
            source: "rble-overlays",
            filter: ["==", ["get", "kind"], "scar_ring"],
            paint: {
              "line-color": "#ff7043",
              "line-width": 3,
              "line-opacity": 0.95,
            },
          });
          map.addLayer({
            id: "axis-marker",
            type: "circle",
            source: "rble-overlays",
            filter: ["==", ["get", "kind"], "preferred_axis"],
            paint: {
              "circle-radius": 9,
              "circle-color": "#3fb950",
              "circle-stroke-color": "#ffffff",
              "circle-stroke-width": 2,
            },
          });

          (map as maplibregl.Map & { setFog?: (f: Record<string, unknown>) => void }).setFog?.({
            color: "#0d1117",
            "high-color": "#161b22",
            "horizon-blend": 0.08,
            "space-color": "#010409",
            "star-intensity": 0.35,
          });
          setLoading(false);
        };

        if (map.isStyleLoaded()) onReady();
        else map.once("load", onReady);
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      }
    };

    map.on("load", loadSky);

    return () => {
      cancelled = true;
      if (spinRef.current !== null) cancelAnimationFrame(spinRef.current);
      map.remove();
      mapRef.current = null;
    };
  }, [product, nside]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !spinning) {
      if (spinRef.current !== null) {
        cancelAnimationFrame(spinRef.current);
        spinRef.current = null;
      }
      return;
    }

    let bearing = map.getBearing();
    const step = () => {
      bearing = (bearing + 0.12) % 360;
      map.setBearing(bearing);
      spinRef.current = requestAnimationFrame(step);
    };
    spinRef.current = requestAnimationFrame(step);
    return () => {
      if (spinRef.current !== null) cancelAnimationFrame(spinRef.current);
    };
  }, [spinning, loading]);

  return (
    <div className={`sky-maplibre ${className}`.trim()}>
      <div className="sky-maplibre-header">
        <div>
          <div className="sky-maplibre-title">{title}</div>
          <div className="sky-maplibre-sub">
            {product === "wmap_k_band" ? "WMAP Ka-band" : "Planck SMICA"} · NSIDE {nside}
            {meta.rble_score != null && (
              <span className="sky-score"> · S_RBLE={meta.rble_score.toFixed(3)}</span>
            )}
            {meta.null_sigma != null && (
              <span className="muted"> · σ_null={meta.null_sigma.toFixed(2)}</span>
            )}
          </div>
        </div>
        {showControls && (
          <div className="sky-maplibre-controls">
            <select
              className="proj-select"
              value={product}
              onChange={(e) => setProduct(e.target.value as SkyMapProduct)}
            >
              <option value="wmap_k_band">WMAP Ka</option>
              <option value="planck_smica_cmb">Planck SMICA</option>
            </select>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={spinning}
                onChange={(e) => setSpinning(e.target.checked)}
              />
              Spin globe
            </label>
          </div>
        )}
      </div>
      <div className="sky-maplibre-canvas" style={{ height }} ref={containerRef} />
      {loading && <div className="sky-maplibre-loading">Loading real sky map…</div>}
      {error && <p className="error sky-maplibre-error">{error}</p>}
      <div className="sky-maplibre-legend">
        <span className="legend-item">
          <span className="legend-swatch cmb" /> CMB temperature (µK)
        </span>
        <span className="legend-item">
          <span className="legend-swatch ring" /> RBLE scar ring
        </span>
        <span className="legend-item">
          <span className="legend-swatch axis" /> Preferred axis
        </span>
      </div>
    </div>
  );
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}
