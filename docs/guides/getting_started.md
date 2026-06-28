# Getting Started with Deepiri Omnifold

**deepiri-omnifold** implements the **RBLE** (Radon-Bifurcated Landscape Engine) — a research stack for choice-driven multiverse simulation and CMB scar detection.

---

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- Optional: CUDA GPU for `omnifold_neural` (PyTorch group)
- Optional: [deepiri-uqe](https://github.com/deepiri/deepiri-uqe) for entanglement bridge

---

## Installation

```bash
cd /home/josep/projects/Deepiri/deepiri-omnifold
poetry install
```

### Optional extras

```bash
# Neural acceleration (Graph-NODE, PINN, scar classifier)
poetry install -E torch

# UQE entanglement bridge
poetry install -E uqe

# Development tools (pytest, ruff, jupyterlab)
poetry install -E dev

# All extras
poetry install -E torch -E uqe -E dev
```

---

## Verify Installation

```bash
poetry run pytest tests/unit/test_conservation.py -v
poetry run pytest tests/unit/test_unified_state.py -v
```

Conservation tests enforce the RBLE closure identity:

$$
\oint_{\mathcal{H}} \Phi_{\text{stream}} \cdot dA = \mathrm{Tr}(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu})
$$

---

## Quick Python Smoke Test

```python
import numpy as np
from omnifold_core.state.unified_state import UnifiedStateVector
from omnifold_core.gravity.information_tensor import information_tensor_N, trace_I_squared
from omnifold_core.conservation import enforce_stream_entropy_closure, stream_flux_integral

# Unified state Ψ(t) = [X, P, Λ_laws, C_choice]
psi = UnifiedStateVector(
    x_spatial=np.array([0.0, 0.0, 0.0]),
    p_momentum=np.array([1.0, 0.0, 0.0]),
    lambda_laws=np.array([1.0, 9.81]),
    c_choice=np.array([0.1, -0.2, 0.3, 0.0, 0.1]),
)

# 5-choice information tensor
I = information_tensor_N(num_choices=5, entropy_gradient=np.array([1.0, 0.0, 0.0, 0.0]))
tr_I2 = trace_I_squared(I)

# Stream with matching flux
phi_stream = np.array([1.0, 0.0, 0.0, 0.0])
horizon_area = tr_I2 / np.linalg.norm(phi_stream)

assert enforce_stream_entropy_closure(phi_stream, tr_I2, horizon_area=horizon_area)
print("RBLE conservation OK")
```

---

## CLI Overview

After install, the `omnifold` command is available:

```bash
poetry run omnifold --help
poetry run omnifold simulate --choices 5 --districts 1
poetry run omnifold scan --synthetic --nside 64
```

See [running_simulations.md](./running_simulations.md) and [cmb_data_pipeline.md](./cmb_data_pipeline.md).

---

## Theory Documentation

Read these before running experiments:

| Document | Content |
|----------|---------|
| [../theory/RBLE_MASTER_EQUATIONS.md](../theory/RBLE_MASTER_EQUATIONS.md) | Eight connected equations |
| [../theory/NOTATION.md](../theory/NOTATION.md) | Symbol table |
| [../theory/VARIATIONAL_PRINCIPLE.md](../theory/VARIATIONAL_PRINCIPLE.md) | Master action $\mathcal{S}_{\text{RBLE}}$ |
| [../theory/FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md) | Testable predictions |

---

## Jupyter Experiments

Numbered notebooks under `experiments/`:

| Notebook | Topic |
|----------|-------|
| `01_district_graph_branching.ipynb` | District DAG, branch weights |
| `02_radon_vacuum_stream.ipynb` | Radon pipeline + conservation |
| `03_wdw_superspace_spawn.ipynb` | Wheeler–DeWitt wavepackets |
| `04_fokker_planck_directed_diffusion.ipynb` | $D_{\text{eff}}$ modification |
| `05_cmb_radon_scar_scan.ipynb` | $\mathcal{S}_{\text{RBLE}}$ on sky |
| `06_er_epr_bridge_uqe.ipynb` | UQE conductance (optional) |

Launch lab environment:

```bash
poetry run jupyter lab experiments/
```

Or use Docker: see `docker/docker-compose.yml` (omnifold-lab service).

---

## Architecture Reference

System diagram and module map: [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md).

---

## Next Steps

1. Run unit tests: `poetry run pytest tests/unit/ -v`
2. Run integration loop: `poetry run pytest tests/integration/test_full_loop.py -v`
3. Follow [running_simulations.md](./running_simulations.md) for district simulations
4. Follow [cmb_data_pipeline.md](./cmb_data_pipeline.md) for sky scans
5. Optional: [uqe_bridge.md](./uqe_bridge.md) for deepiri-uqe integration
