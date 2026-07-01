import { useCallback, useEffect, useRef, useState } from "react";
import {
  loadAladin,
  type AladinCatalog,
  type AladinFactory,
  type AladinInstance,
} from "../aladin/types";

export type SkyWorld = {
  frame: "galactic" | "equatorial";
  surveys: Record<string, { id: string; name: string; mission: string; band: string }>;
  default_survey: string;
  cmb_products: Record<string, string>;
  rble: {
    metadata: {
      rble_score?: number;
      null_sigma?: number;
      map_product_id?: string;
    };
    scar_ring: number[][];
    axis: number[];
  };
  gw_events: Array<{
    name: string;
    ra: number;
    dec: number;
    glon: number;
    glat: number;
    catalog: string;
  }>;
  sdss_objects: Array<{ ra: number; dec: number; glon?: number; glat?: number; z: number; kind: string }>;
};

type Props = {
  mapProduct?: string;
  nside?: number;
  height?: number;
  title?: string;
  className?: string;
};

const SURVEY_KEYS = ["dss2", "2mass", "wise", "planck143", "cmb_wmap", "cmb_planck"] as const;

export default function AladinSkyViewer({
  mapProduct = "wmap_k_band",
  nside = 64,
  height = 520,
  title = "Live Cosmos Observatory",
  className = "",
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const aladinRef = useRef<AladinInstance | null>(null);
  const catalogsRef = useRef<AladinCatalog[]>([]);
  const [world, setWorld] = useState<SkyWorld | null>(null);
  const [survey, setSurvey] = useState("dss2");
  const [frame, setFrame] = useState<"galactic" | "equatorial">("galactic");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cvResult, setCvResult] = useState<string | null>(null);
  const [cvRunning, setCvRunning] = useState(false);
  const [gwLive, setGwLive] = useState(0);

  const loadWorld = useCallback(async () => {
    const res = await fetch(
      `/cosmos/sky/world?map_product=${mapProduct}&nside=${nside}&frame=${frame}`,
    );
    if (!res.ok) throw new Error(`/cosmos/sky/world → ${res.status}`);
    return res.json() as Promise<SkyWorld>;
  }, [mapProduct, nside, frame]);

  const applyOverlays = useCallback(
    (A: AladinFactory, aladin: AladinInstance, data: SkyWorld) => {
      catalogsRef.current.forEach((c) => {
        try {
          c.remove();
        } catch {
          /* ignore */
        }
      });
      catalogsRef.current = [];

      const useGalactic = data.frame === "galactic";
      const pos = (lon: number, lat: number) =>
        useGalactic ? { lon, lat } : { ra: lon, dec: lat };

      const scarCat = A.catalog({ name: "RBLE scar ring", color: "#ff7043", shape: "plus" });
      scarCat.addSources(
        data.rble.scar_ring.map(([lon, lat], i) => ({
          ...pos(lon, lat),
          name: `scar_${i}`,
        })),
      );
      aladin.addCatalog(scarCat);
      catalogsRef.current.push(scarCat);

      const axisCat = A.catalog({ name: "RBLE axis", color: "#3fb950", shape: "star" });
      const [alon, alat] = data.rble.axis;
      axisCat.addSources([
        {
          ...pos(alon, alat),
          name: `S=${data.rble.metadata.rble_score?.toFixed(3) ?? "?"}`,
        },
      ]);
      aladin.addCatalog(axisCat);
      catalogsRef.current.push(axisCat);

      const gwCat = A.catalog({ name: "GW live (LIGO/Virgo)", color: "#58a6ff", shape: "circle" });
      gwCat.addSources(
        data.gw_events.map((e) => ({
          ...(useGalactic ? { lon: e.glon, lat: e.glat } : { ra: e.ra, dec: e.dec }),
          name: e.name,
        })),
      );
      aladin.addCatalog(gwCat);
      catalogsRef.current.push(gwCat);

      const sdssCat = A.catalog({ name: "SDSS galaxies/QSOs", color: "#d29922", shape: "square" });
      sdssCat.addSources(
        data.sdss_objects.map((o) => ({
          ...(useGalactic
            ? { lon: o.glon ?? o.ra, lat: o.glat ?? o.dec }
            : { ra: o.ra, dec: o.dec }),
          name: `${o.kind} z=${o.z.toFixed(2)}`,
        })),
      );
      aladin.addCatalog(sdssCat);
      catalogsRef.current.push(sdssCat);
    },
    [],
  );

  const setSurveyLayer = useCallback(
    (aladin: AladinInstance, data: SkyWorld, surveyKey: string) => {
      const meta = data.surveys[surveyKey];
      if (!meta) return;

      if (surveyKey === "cmb_wmap" || surveyKey === "cmb_planck") {
        const product =
          surveyKey === "cmb_wmap" ? "wmap_k_band" : "planck_smica_cmb";
        const raster = `/cosmos/sky/raster?map_product=${product}&nside=${nside}&width=2048&height=1024`;
        try {
          const layer = aladin.createImageSurvey(
            meta.name,
            meta.id,
            raster,
            data.frame === "galactic" ? "galactic" : "equatorial",
            { imgFormat: "png", colormap: "rainbow" },
          );
          aladin.setBaseImageLayer(layer);
        } catch {
          aladin.setImageSurvey("P/DSS2/color");
        }
        return;
      }

      try {
        if (typeof aladin.newImageSurvey === "function") {
          aladin.setBaseImageLayer(aladin.newImageSurvey(meta.id));
        } else {
          aladin.setImageSurvey(meta.id);
        }
      } catch {
        aladin.setImageSurvey("P/DSS2/color");
      }
    },
    [nside],
  );

  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;
    if (!host) return;

    host.innerHTML = "";
    const mountId = `aladin-${Math.random().toString(36).slice(2)}`;
    const mount = document.createElement("div");
    mount.id = mountId;
    mount.style.width = "100%";
    mount.style.height = "100%";
    host.appendChild(mount);

    setLoading(true);
    setError(null);

    (async () => {
      try {
        const A = await loadAladin();
        const data = await loadWorld();
        if (cancelled) return;
        setWorld(data);

        const aladin = A.aladin(`#${mountId}`, {
          fov: 360,
          projection: "AIT",
          cooFrame: frame,
          showSimbadPointerControl: true,
          showCooGridControl: true,
          showCooGrid: true,
          showFullscreenControl: true,
          showZoomControl: true,
          showReticle: true,
          target: frame === "galactic" ? "0 0 galactic" : "0 0 equatorial",
        });
        aladinRef.current = aladin;
        aladin.setProjection("AIT");
        setSurveyLayer(aladin, data, survey);
        applyOverlays(A, aladin, data);
        if (!cancelled) setLoading(false);
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      aladinRef.current = null;
      host.innerHTML = "";
    };
  }, [loadWorld, frame, applyOverlays, setSurveyLayer]);

  useEffect(() => {
    const aladin = aladinRef.current;
    if (!aladin || !world) return;
    setSurveyLayer(aladin, world, survey);
  }, [survey, world, setSurveyLayer]);

  useEffect(() => {
    const es = new EventSource("/stream/gw/poll?interval=30&max_events=9999");
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as { new_events?: number };
        if (typeof payload.new_events === "number") setGwLive(payload.new_events);
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, []);

  const runCvScan = async () => {
    setCvRunning(true);
    setCvResult(null);
    try {
      const res = await fetch("/observatory/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nside,
          synthetic: false,
          map_product: mapProduct,
          nulls: 25,
          seed: 0,
        }),
      });
      const data = await res.json();
      setCvResult(
        `CV scan: S_RBLE=${Number(data.rble_score ?? 0).toFixed(4)} · σ=${Number(data.null_sigma ?? 0).toFixed(2)}`,
      );
      const fresh = await loadWorld();
      setWorld(fresh);
      if (aladinRef.current && window.A) {
        applyOverlays(window.A, aladinRef.current, fresh);
      }
    } catch (e) {
      setCvResult(`CV scan failed: ${e}`);
    } finally {
      setCvRunning(false);
    }
  };

  return (
    <div className={`aladin-sky ${className}`.trim()}>
      <div className="aladin-sky-header">
        <div>
          <div className="aladin-sky-title">{title}</div>
          <div className="aladin-sky-sub">
            Aladin Lite · IVOA HiPS real surveys · GWOSC live · SDSS · RBLE CV
            {world?.rble.metadata.rble_score != null && (
              <span className="sky-score">
                {" "}
                · S_RBLE={world.rble.metadata.rble_score.toFixed(3)}
              </span>
            )}
            {gwLive > 0 && <span className="ok-text"> · {gwLive} new GW events</span>}
          </div>
        </div>
        <div className="aladin-sky-controls">
          <select
            className="proj-select"
            value={survey}
            onChange={(e) => setSurvey(e.target.value)}
          >
            {SURVEY_KEYS.map((k) => (
              <option key={k} value={k} disabled={!world?.surveys[k]}>
                {world?.surveys[k]?.name ?? k}
              </option>
            ))}
          </select>
          <select
            className="proj-select"
            value={frame}
            onChange={(e) => setFrame(e.target.value as typeof frame)}
          >
            <option value="galactic">Galactic</option>
            <option value="equatorial">Equatorial (ICRS)</option>
          </select>
          <button disabled={cvRunning} onClick={runCvScan}>
            {cvRunning ? "CV scanning…" : "RBLE CV Scan"}
          </button>
        </div>
      </div>
      <div className="aladin-sky-canvas" style={{ height }}>
        <div ref={hostRef} className="aladin-sky-mount" />
        {loading && <div className="sky-maplibre-loading">Loading real sky surveys…</div>}
      </div>
      {cvResult && <p className="aladin-cv-result">{cvResult}</p>}
      {error && <p className="error aladin-sky-error">{error}</p>}
      <div className="sky-maplibre-legend">
        <span className="legend-item">
          <span className="legend-swatch ring" /> RBLE scar ring
        </span>
        <span className="legend-item">
          <span className="legend-swatch axis" /> Preferred axis
        </span>
        <span className="legend-item">
          <span className="legend-swatch gw" /> GW transients (live catalog)
        </span>
        <span className="legend-item">
          <span className="legend-swatch sdss" /> SDSS spectroscopy
        </span>
      </div>
    </div>
  );
}
