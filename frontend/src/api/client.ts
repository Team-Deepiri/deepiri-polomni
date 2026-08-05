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

export type WorldMethodInfo = {
  n_worlds: number;
  order_parameter_s: number;
  preferred_axis: number[];
  eigenvalues: number[];
  separation_from_galactic_pole_deg: number;
};

export type WorldScan = {
  rble_score: number;
  preferred_axis: number[];
  null_mu: number;
  null_sigma: number;
  null_sigma_significance: number;
  n_ensemble: number;
  weight: string;
  separation_from_galactic_pole_deg: number;
  metadata: Record<string, unknown>;
};

export type WorldAtlas = {
  ready: boolean;
  source: string;
  nside: number;
  weight: string;
  catalog: {
    n_worlds: number;
    n_hosts: number;
    n_planets_sky: number;
    occupied_pixels: number;
    occupancy_fraction: number;
    years_range: number[];
    methods: string[];
  };
  scan: WorldScan;
  axis_marker: { lon: number; lat: number };
  scar_ring: { lon: number[]; lat: number[] };
  alignment: {
    n_worlds: number;
    trace: number;
    eigenvalues: number[];
    preferred_axis: number[];
    order_parameter_s: number;
    lam1_minus_isotropic: number;
  };
  methods: Record<string, WorldMethodInfo>;
  points: {
    lon: number[];
    lat: number[];
    name: string[];
    host: string[];
    period_days: (number | null)[];
    st_teff: (number | null)[];
    radius_earth: (number | null)[];
    disc_year: (number | null)[];
    method: string[];
    eq_temp: (number | null)[];
    n_worlds: number;
  };
  timestamp: string;
};

export type CosmosSnapshot = {
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

export type DistrictGraphNode = {
  id: string;
  mass: number;
  x: number;
  y: number;
  z: number;
};

export type DistrictGraphEdge = {
  source: string;
  target: string;
  conductance: number;
};

export type DistrictGraphData = {
  nodes: DistrictGraphNode[];
  edges: DistrictGraphEdge[];
};

export type ClosedLoopStep = {
  step: number;
  true_axis: number[];
  recovered_axis: number[];
  axis_error_deg: number;
  rble_score: number;
  graph_nodes: number;
  graph_edges: number;
};

export type ClosedLoopPanel = {
  steps: ClosedLoopStep[];
  graph: DistrictGraphData;
  final_axis_error_deg: number | null;
  cmb_values: number[];
  cmb_lon?: number[];
  cmb_lat?: number[];
  nside: number;
  true_axis?: number[];
  recovered_axis?: number[];
};

export type PhysicsLoopStep = {
  step: number;
  synthetic_axis: number[];
  real_axis: number[];
  separation_deg: number;
  alignment_quality: number;
  rble_score: number;
};

export type PhysicsLoopPanel = {
  map_product_id: string;
  nside: number;
  real_axis: number[];
  real_score: number;
  steps: PhysicsLoopStep[];
  final_separation_deg: number | null;
  final_alignment_quality: number | null;
  graph?: DistrictGraphData;
};

export type NeuralCorpusSummary = {
  n_runs: number;
  n_samples: number;
  max_nodes: number;
  max_branches: number;
  mean_axis_error_deg: number;
  source_dir?: string;
};

export const api = {
  health: () => fetchJson<{ status: string }>("/health"),
  metrics: () => fetchJson<Record<string, unknown>>("/metrics"),
  prove: () =>
    fetch(`${API}/math/prove`, { method: "POST" }).then((r) => r.json()),
  proofs: () => fetchJson<{ cached: boolean; results?: unknown[] }>("/math/proofs"),
  districtGraph: (opts?: { choices?: number; districts?: number; steps?: number; policy?: string }) => {
    const q = new URLSearchParams();
    q.set("choices", String(opts?.choices ?? 5));
    q.set("districts", String(opts?.districts ?? 1));
    q.set("steps", String(opts?.steps ?? 2));
    q.set("policy", opts?.policy ?? "uniform");
    return fetchJson<DistrictGraphData>(`/viz/district-graph?${q}`);
  },
  closedLoop: (opts?: { steps?: number; choices?: number; nside?: number; policy?: string }) => {
    const q = new URLSearchParams();
    q.set("steps", String(opts?.steps ?? 3));
    q.set("choices", String(opts?.choices ?? 4));
    q.set("nside", String(opts?.nside ?? 32));
    q.set("policy", opts?.policy ?? "axis_biased");
    return fetchJson<ClosedLoopPanel>(`/viz/closed-loop?${q}`);
  },
  physicsLoop: (opts?: { steps?: number; nside?: number; mapProduct?: string }) => {
    const q = new URLSearchParams();
    q.set("steps", String(opts?.steps ?? 3));
    q.set("nside", String(opts?.nside ?? 32));
    q.set("map_product", opts?.mapProduct ?? "wmap_k_band");
    return fetchJson<PhysicsLoopPanel>(`/viz/physics-loop?${q}`);
  },
  neuralCorpus: () => fetchJson<NeuralCorpusSummary>("/viz/neural-corpus"),
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
  cosmosWorlds: (opts?: { nside?: number; weight?: string; nEnsemble?: number }) => {
    const q = new URLSearchParams();
    q.set("nside", String(opts?.nside ?? 32));
    q.set("weight", opts?.weight ?? "count");
    q.set("n_ensemble", String(opts?.nEnsemble ?? 40));
    return fetchJson<WorldAtlas>(`/cosmos/worlds?${q}`);
  },
};
