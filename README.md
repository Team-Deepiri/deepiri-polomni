# deepiri-polomni — Deepiri Polomni Engine

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

> A research-ready computational cosmology lab implementing **RBLE** — the Radon-Bifurcated Landscape Engine — for choice-driven multiverse simulation, Radon-vacuum streaming, and CMB observatory validation.
<img width="1277" height="666" alt="image" src="https://github.com/user-attachments/assets/a07eba7f-66c8-46f4-a430-5c33cbe97861" />

---

## Vision

**deepiri-polomni** is a living research sandbox at the intersection of:

- **Choice-driven cosmology** — N-way bifurcations map to graviton wells and spatial districts
- **String landscape** — Kähler potential and flux compactification set local physical laws
- **Radon-vacuum streaming** — districts compress via Radon transforms, rotate under SO(3), and stream through horizons
- **Wheeler–DeWitt superspace** — vacuum streams spawn child universes as wavepackets
- **CMB observatory** — search real sky maps for Radon-bifurcation scars

This is an active lab. Core physics ships as tested, typed Python modules. Experiments ship as notebooks.

**Roadmap:** see [ROADMAP.md](ROADMAP.md) for the 4-week plan (2 devs).

**Establishing RBLE as physics:** see [docs/PHYSICS_ESTABLISHMENT.md](docs/PHYSICS_ESTABLISHMENT.md) — pre-registered P1 CMB scar search, blind holdout protocol, and replication package.

**Replicate P1 blind holdout:** see [docs/REPLICATION.md](docs/REPLICATION.md) — `make reproduce-p1`  
**Gate 5 verify:** `poetry run polomni study replicate` — [docs/guides/REPLICATION_P1.md](docs/guides/REPLICATION_P1.md)

```bash
./setup.sh --dev --run                      # install + interactive lab menu
poetry run polomni run live                 # real data: fetch → gates → P1 → physics loop
poetry run polomni run live --blind         # + Planck holdout (one-shot)
poetry run polomni study gates              # Gates 1–3 before holdout
poetry run polomni study run p1 --blind     # one-shot Planck holdout
```

---

## RBLE — Radon-Bifurcated Landscape Engine

| Letter | Meaning |
|--------|---------|
| **R** | **Radon** — holographic district encapsulation and CMB scar detection |
| **B** | **Bifurcated** — N-choice topological domain splitting at graviton wells |
| **L** | **Landscape** — string-theory flux vacua and Kähler stabilization |
| **E** | **Engine** — closed computational loop from choice → stream → superspace → sky |

The unified state vector stacks every district degree of freedom:

```
Ψ(t) = [ X_spatial ; P_momentum ; Λ_laws ; C_choice ]
```

Conservation at the horizon (Connected Equation 4):

```
∫_Ω ∇_μ J^μ_choice d⁴x  =  Tr(I_μν I^μν)  =  ∮_H Φ_stream · dA
```

---

## Repository Structure

```
deepiri-polomni/
├── src/polomni/core/              # RBLE physics engine
│   ├── state/                  # Ψ(t), StreamPacket, ChoiceEvent
│   ├── landscape/              # Kähler potential, flux vacua
│   ├── gravity/                # Einstein + informational stress
│   ├── inflation/              # Fokker-Planck eternal inflation
│   ├── superspace/             # District graph, branch operators
│   ├── radon/                  # R³/S² transforms, vacuum pipeline
│   ├── conductance/            # ER=EPR bridge tensor
│   └── simulation/             # Batch district simulations
├── src/polomni/neural/            # Graph-NODE / neural ODE layers
├── src/polomni/observatory/       # CMB Radon scar detection
│   └── pipeline/               # Real-data fetch, cache, ingest, watch loop
├── src/polomni/api/               # FastAPI REST surface (`polomni serve`)
├── src/polomni/integration/       # Lab workflow orchestration & benchmarks
├── src/polomni/bridge/            # Optional cross-sector coupling (NumPy stubs)
├── src/polomni/cli/               # Typer CLI (`polomni`)
├── src/polomni/viz/               # Plots and sky maps
├── tests/                      # Unit, integration, observatory suites
├── docs/                       # Theory, guides, architecture
├── experiments/                # Jupyter notebooks
└── docker/                     # Reproducible environment
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)

### Install

```bash
cd deepiri-polomni
poetry install
```

Optional dependency groups:

```bash
# Neural ODE / Graph-NODE layers
poetry install --with torch

# Development tools
poetry install --with dev
```

### Verify

```bash
poetry run pytest tests/unit -q
poetry run polomni simulate --choices 5 --districts 1
```

### Minimal API Example

```python
import numpy as np
from polomni.core import (
    UnifiedStateVector,
    compute_information_trace,
    enforce_stream_entropy_closure,
    stream_flux_integral,
)

# District state Ψ(t)
state = UnifiedStateVector(
    X_spatial=np.array([1.0, 0.0, 0.0]),
    P_momentum=np.array([0.0, 1.0, 0.0]),
    Lambda_laws=np.array([1.0e-122]),  # Λ from string landscape
    C_choice=np.array([0.2, 0.2, 0.2, 0.2, 0.2]),  # 5-way choice
)

# Information tensor for N=5 split
i_tensor = np.diag([0.6, 0.8])
trace = compute_information_trace(i_tensor)

# Vacuum stream closure at horizon
phi = np.full(5, trace / 5.0)
assert enforce_stream_entropy_closure(phi, trace)
print(f"Ψ dim={state.dim}, flux={stream_flux_integral(phi, 1.0):.4f}")
```

---

## Real Data Pipeline

Fetch public CMB and GW catalogs, cache locally, and run the full RBLE observatory pipeline on real sky maps.

| Command | Description |
|---------|-------------|
| `polomni data list` | Show the online data catalog (Planck, WMAP, GWOSC, NASA exoplanets) |
| `polomni data status` | List cached files and sizes under `data/cache/` |
| `polomni data fetch` | Download lite products + GWTC (use `--wmap`, `--planck` for maps) |
| `polomni data pipeline` | Ingest cached data and run RBLE scan (default WMAP K-band, NSIDE 128) |
| `polomni data worlds` | Scan the real NASA exoplanet sky with RBLE + footprint null + dipole + C_ℓ |
| `polomni data watch` | Poll GWOSC on an interval; optional `--scan-on-gw` re-scan |
| `polomni data plot power` | Plot cached CMB power spectrum PNG |
| `polomni data plot gw` | Plot GW event timeline from cache |
| `polomni data correlate` | Match GW events to RBLE preferred axis |

```bash
# Lite cosmology products (~KB) + GW catalog
poetry run polomni data fetch

# Fast pipeline smoke test
poetry run polomni data pipeline --nside 64 --nulls 10

# Real-time GW polling (3 cycles, 60 s apart)
poetry run polomni data watch --interval 60 --iterations 3
```

Cache directory: `data/cache/` (override with `POLOMNI_DATA_CACHE`). See [docs/guides/real_time_data.md](docs/guides/real_time_data.md).

---

## World Atlas — NASA Exoplanet Archive

Maps the **real sky positions of every confirmed exoplanet** (NASA Exoplanet Archive,
`nasa_exoplanet_ps`) onto a HEALPix density map, runs the RBLE geodesic-Radon scar
scan over the distribution of worlds, and reports **four checks** that a
naive scan would fake:

1. **Footprint-matched null** — world counts are reshuffled *within* the observed
   survey mask (Kepler field, TESS bands), so the reported σ is against an honest null,
   not an unreachable isotropic sky.
2. **Per-method axis audit** — the preferred axis is recomputed per discovery method
   and referenced to the Galactic pole. Sky-complete Radial Velocity worlds are nearly
   isotropic (S≈0.06); Microlensing worlds are ordered *in the Galactic plane*
   (S≈0.98, 88° from pole). A genuine world scar must survive both checks.
3. **World-dipole cosmic-rest-frame test** — the dipole of the world directions is
   measured against the CMB dipole apex (the Solar System's motion through the cosmic
   rest frame), the ecliptic pole, the Galactic pole, and the Kepler field. Current
   result: the dipole sits **4.8° from the Kepler field** and ≥62° from every cosmic
   reference — a physical anisotropy would point at the CMB rest frame; this points at
   the survey footprint.
4. **World-sky power spectrum C_ℓ** — a novel observable (no published spectrum exists
   for the confirmed-planet sky) with a uniform-within-footprint null. Only ℓ=1 (the
   Kepler dipole) exceeds the null at ~6.5σ; all ℓ≥2 are consistent with random
   placement within the footprint.
5. **Cross-sky axis test** — independent skies must agree on a preferred axis, or there
   is no axis. Compares the world dipole across every cached independent sky. Current
   result: **exoplanets ↔ SDSS galaxies disagree by 71.9°** — each dipole points at its
   own survey footprint (exoplanets → Kepler 4.8°, SDSS → northern cap). GWTC
   `network_axis` is detector geometry and is rejected, not shipped as a sky direction.
6. **Bubble-collision search** — the one multiverse signature with a concrete
   observable: in eternal inflation a bubble colliding with ours leaves a **circular
   temperature edge** in the CMB. Scans the real Planck SMICA map for such edges against
   a C_ℓ- and mask-matched null (look-elsewhere corrected), validated by an injection
   gate that recovers planted collisions exactly. Current result: **no significant edge
   (p≈0.35)** — consistent with the published null (Feeney et al. 2011), and the
   strongest circle's radial profile is a smooth gradient, not a step.

```bash
poetry run polomni data fetch nasa_exoplanet_ps sdss_bao_ladder
poetry run polomni data worlds --nside 32 --ensemble 40 --null 100
poetry run polomni data cross-sky
poetry run polomni data bubble --nside 128 --n-null 16
```

The **World Atlas** panel in the frontend (`/app`) renders all worlds on a MapLibre
globe colored by host temperature (or discovery method), with the RBLE scar ring +
preferred axis overlaid, the world-dipole marker, the C_ℓ spectrum chart, and the full
selection-bias audit table.

Theory, invariants (Tr(Q)≡1), and domain of validity: [docs/theory/WORLD_ATLAS.md](docs/theory/WORLD_ATLAS.md).

---

## REST API

Start the lab API with FastAPI on port **8091** (default):

```bash
poetry run polomni serve
# or: poetry run polomni serve --host 0.0.0.0 --port 8091
```

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness probe |
| `/` | GET | Service metadata |
| `/data/catalog` | GET | List fetchable data products |
| `/data/status` | GET | Cache hit/miss per product |
| `/data/fetch` | POST | Download products into cache |
| `/data/gw/events` | GET | Cached GWTC event summary |
| `/observatory/scan` | POST | RBLE scar scan (synthetic or cached map) |
| `/observatory/pipeline` | POST | Full ingest → score → report pipeline |
| `/observatory/reports` | GET | List JSON detection reports |
| `/observatory/compare` | POST | Compare two detection reports |
| `/cosmos/worlds` | GET | World Atlas — RBLE scan of real exoplanet sky positions + footprint null |
| `/metrics` | GET | Lab operational metrics |
| `/dashboard` | GET | Browser dashboard UI |
| `/stream/gw/poll` | GET | SSE stream of GW catalog poll events |

Full request/response schemas: [docs/guides/api_reference.md](docs/guides/api_reference.md). Curl walkthrough: [experiments/08_api_workflow.ipynb](experiments/08_api_workflow.ipynb).

---

## Lab Workflow

Run the integrated end-to-end lab loop — data ingest, short district-graph simulation, and RBLE pipeline — in one command:

```bash
poetry run polomni run workflow --nside 64 --nulls 10
poetry run polomni run workflow -o data/reports/lab_workflow.json
```

Profile RBLE signature timing across NSIDE resolutions:

```bash
poetry run polomni run benchmark --nside 16 --nside 32 --nside 64
```

Implementation: `src/polomni/integration/workflow.py`. Architecture: [docs/architecture/DATA_PIPELINE.md](docs/architecture/DATA_PIPELINE.md).

---

## Visualization

Generate publication-style figures from the CLI:

| Command | Description |
|---------|-------------|
| `polomni viz sky` | Mollweide CMB map (`--real` uses cached WMAP/Planck product) |
| `polomni viz district` | District branching DAG after choice events |
| `polomni viz stream` | Radon vacuum stream flux stages |

```bash
poetry run polomni viz sky --real --map-product wmap_k_band --nside 64
poetry run polomni viz district --districts 2 --choices 5
poetry run polomni viz stream --packets 5 -o data/figures/stream_demo.png
```

Figures default to `data/figures/`. Use `polomni info` to inspect cache state and optional dependencies.

---

## Reports & Hierarchical Search

Manage and compare RBLE detection reports:

```bash
poetry run polomni report list
poetry run polomni report latest
poetry run polomni report compare data/reports/run_a.json data/reports/run_b.json
```

Coarse-to-fine sky search for high-resolution maps:

```bash
poetry run polomni scan --real --hierarchical --nside 128
```

---

## Setup & Lab Menu

```bash
./setup.sh --dev                  # poetry + npm install
./setup.sh --dev --run            # install, then interactive menu
poetry run polomni run menu       # menu only (proof, corpus, train, serve, …)
poetry run polomni run            # same as menu
```

Existing helper scripts in `scripts/` (p1-gates, verify-stack, dev-up, etc.) still work.

```bash
poetry run polomni simulate batch --count 10 --choices 5
bash scripts/verify-stack.sh      # full stack smoke
bash scripts/dev-up.sh            # start lab + Jupyter
```

Docker watch profile for continuous GW polling:

```bash
docker compose -f docker/docker-compose.yml --profile watch up -d
```

---

## Math Proofs & Multiverse Frontend

Run the full RBLE equation proof suite:

```bash
poetry run polomni math prove
poetry run polomni math equations
```

| Endpoint | Purpose |
|----------|---------|
| `GET /math/equations` | Equation catalog |
| `POST /math/prove` | Run all proofs |
| `GET /viz/district-graph` | 3D multiverse DAG data |
| `GET /viz/landscape` | Kähler surface grid |
| `GET /viz/scar-sphere` | HEALPix scar + axis |
| `GET /viz/falsification` | P1–P3 status |

**React frontend** (`frontend/`):

```bash
poetry run polomni serve --port 8091
cd frontend && npm install && npm run dev   # http://localhost:5173
cd frontend && npm run build                # production → http://localhost:8091/app
```

Panels include the **World Atlas** (real NASA exoplanets + RBLE scan), Cosmos Lab
(WMAP/Planck dual-map calibration), 3D multiverse DAG, Kähler landscape, and the proof
suite.

Proof notebooks: `experiments/09_variational_principle.ipynb` through `13_real_data_theory_bridge.ipynb`.

See [docs/guides/frontend.md](docs/guides/frontend.md).

---

## Related Deepiri Repos

| Repo | Role |
|------|------|
| [deepiri-uqe](https://github.com/deepiri/deepiri-uqe) | Universal Quantum Engine — optional entanglement / ER=EPR layers |

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
