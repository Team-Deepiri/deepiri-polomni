const API = "";

export async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchJson<{ status: string }>("/health"),
  metrics: () => fetchJson<Record<string, unknown>>("/metrics"),
  prove: () =>
    fetch(`${API}/math/prove`, { method: "POST" }).then((r) => r.json()),
  proofs: () => fetchJson<{ cached: boolean; results?: unknown[] }>("/math/proofs"),
  districtGraph: (choices = 5) => fetchJson(`/viz/district-graph?choices=${choices}`),
  landscape: () => fetchJson("/viz/landscape"),
  scarSphere: (nside = 32) => fetchJson(`/viz/scar-sphere?synthetic=true&nside=${nside}`),
  streamFlux: () => fetchJson("/viz/stream-flux"),
  branchSimplex: () => fetchJson("/viz/branch-simplex"),
  falsification: () => fetchJson("/viz/falsification"),
};
