# deepiri-polomni — Deepiri Polomni Engine

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

> A research-ready computational cosmology lab implementing **RBLE** — the Radon-Bifurcated Landscape Engine — for choice-driven multiverse simulation, Radon-vacuum streaming, and CMB observatory validation.

---

## Vision

**deepiri-polomni** is a living research sandbox at the intersection of:

- **Choice-driven cosmology** — N-way bifurcations map to graviton wells and spatial districts
- **String landscape** — Kähler potential and flux compactification set local physical laws
- **Radon-vacuum streaming** — districts compress via Radon transforms, rotate under SO(3), and stream through horizons
- **Wheeler–DeWitt superspace** — vacuum streams spawn child universes as wavepackets
- **CMB observatory** — search real sky maps for Radon-bifurcation scars

This is an active lab. Core physics ships as tested, typed Python modules. Experiments ship as notebooks.

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
├── src/polomni/core/           # RBLE physics engine
│   ├── state/               # Ψ(t), StreamPacket, ChoiceEvent
│   ├── landscape/           # Kähler potential, flux vacua
│   ├── gravity/             # Einstein + informational stress
│   ├── inflation/           # Fokker-Planck eternal inflation
│   ├── superspace/          # District graph, branch operators
│   ├── radon/               # R³/S² transforms, vacuum pipeline
│   └── conductance/         # ER=EPR bridge tensor
├── src/polomni/neural/         # Graph-NODE / neural ODE layers
├── src/polomni/observatory/    # CMB Radon scar detection
├── src/polomni/bridge/         # Optional cross-sector coupling (standalone NumPy stubs)
├── src/polomni/cli/            # Typer CLI (`polomni`)
├── src/polomni/viz/           # Plots and sky maps
├── tests/                   # Unit, integration, observatory suites
├── docs/                    # Theory, guides, architecture
├── experiments/             # Jupyter notebooks
└── docker/                  # Reproducible environment
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

## Related Deepiri Repos

| Repo | Role |
|------|------|
| [deepiri-uqe](https://github.com/deepiri/deepiri-uqe) | Universal Quantum Engine — optional entanglement / ER=EPR layers |

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
