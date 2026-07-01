const API = "";

export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export type CosmosSky = {
  map_product_id: string;
  nside: number;
  lon: number[];
  lat: number[];
  values: number[];
  rble_score: number;
  null_sigma: number;
  preferred_axis: number[];
  axis_marker: { lon: number; lat: number };
  scar_ring: { lon: number[]; lat: number[] };
};

export type CosmosSnapshot = {
  kind: string;
  timestamp: string;
  gates_passed: boolean;
  gates: {
    all_passed: boolean;
    passed: number;
    checks: Array<{ gate: string; name: string; passed: boolean; message: string }>;
  };
  study: Record<string, unknown> | null;
  proofs_passed: number;
  proofs_total: number;
  proofs_all_passed: boolean;
  verify_running?: boolean;
  p1_supported?: boolean;
  p1_falsified?: boolean;
};

export type ProgressEvent = {
  step: string;
  message: string;
  timestamp: string;
  ok?: boolean;
  passed?: boolean;
  p1_supported?: boolean;
};

export const api = {
  health: () => fetchJson<{ status: string }>("/health"),
  metrics: () => fetchJson<Record<string, unknown>>("/metrics"),
  prove: () =>
    fetch(`${API}/math/prove`, { method: "POST" }).then((r) => r.json()),
  proofs: () => fetchJson<{ cached: boolean; results?: unknown[] }>("/math/proofs"),
  districtGraph: (choices = 5) => fetchJson(`/viz/district-graph?choices=${choices}`),
  landscape: () => fetchJson("/viz/landscape"),
  scarSphere: (nside = 32, synthetic = false) =>
    fetchJson(`/viz/scar-sphere?synthetic=${synthetic}&nside=${nside}&map_product=wmap_k_band`),
  streamFlux: () => fetchJson("/viz/stream-flux"),
  branchSimplex: () => fetchJson("/viz/branch-simplex"),
  falsification: () => fetchJson("/viz/falsification"),

  cosmosSky: (nside = 64, product = "wmap_k_band") =>
    fetchJson<CosmosSky>(`/cosmos/sky?nside=${nside}&map_product=${product}`),
  cosmosPowerSpectrum: () => fetchJson("/cosmos/power-spectrum"),
  cosmosNullTiers: (nside = 64, product = "wmap_k_band") =>
    fetchJson(`/cosmos/null-tiers?nside=${nside}&map_product=${product}`),
  cosmosCompare: (nside = 64) => fetchJson(`/cosmos/compare?nside=${nside}`),
  cosmosHistogram: (product = "wmap_k_band", nside = 64) =>
    fetchJson(`/cosmos/null-histogram?nside=${nside}&map_product=${product}`),
  cosmosStudy: () => fetchJson("/cosmos/study"),
  cosmosSnapshot: () => fetchJson<CosmosSnapshot>("/cosmos/snapshot"),
  cosmosVerify: (blind = false) =>
    fetch(`${API}/cosmos/verify?blind=${blind}`, { method: "POST" }).then((r) => r.json()),
  cosmosVerifyStatus: () =>
    fetchJson<{ running: boolean; has_result: boolean; error: string | null }>(
      "/cosmos/verify/status",
    ),
  cosmosVerifyResult: () => fetchJson<{ ready: boolean; [k: string]: unknown }>("/cosmos/verify/result"),
  cosmosTomogram: (product = "wmap_k_band", nside = 64) =>
    fetchJson(`/cosmos/tomogram?nside=${nside}&map_product=${product}`),
  cosmosLandscape: (product = "wmap_k_band", nside = 64) =>
    fetchJson(`/cosmos/landscape?nside=${nside}&map_product=${product}`),
  cosmosSkyOverlays: (nside = 64, product = "wmap_k_band") =>
    fetchJson(`/cosmos/sky/overlays?nside=${nside}&map_product=${product}`),
  cosmosSkyRasterUrl: (nside = 64, product = "wmap_k_band", width = 1536, height = 768) =>
    `/cosmos/sky/raster?nside=${nside}&map_product=${product}&width=${width}&height=${height}`,
};
