# UQE Bridge Guide

Optional integration between **deepiri-omnifold** (RBLE conductance network) and **deepiri-uqe** (quantum entanglement simulation).

**Theory:** Equation 7 in [../theory/RBLE_MASTER_EQUATIONS.md](../theory/RBLE_MASTER_EQUATIONS.md) · **Architecture:** [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md)

---

## Purpose

RBLE quantifies cross-district data leak via the **ER=EPR bridge conductance**:

$$
\mathcal{G}_{ij}(t)
= e^{-S_{\text{Euclidean}}[\text{bridge}_{ij}]/\hbar}
\left\langle \Phi_{\text{stream}}^{(i)} \middle| \hat{T}_{\mu\nu} \middle| \Phi_{\text{stream}}^{(j)} \right\rangle
$$

**deepiri-uqe** supplies density matrices $\rho_i, \rho_j$ and interaction Hamiltonians for entangled branches. The bridge maps these to $\mathcal{G}_{ij}$ on the district graph.

---

## Installation

UQE is **not** a required dependency. Install explicitly:

```bash
cd /home/josep/projects/Deepiri/deepiri-omnifold
poetry install -E uqe
```

This adds a path dependency on `deepiri-uqe` (configure path in `pyproject.toml` to match your local clone).

Verify:

```bash
poetry run python -c "from omnifold_uqe_bridge.entanglement import cross_branch_gradient; print('UQE bridge OK')"
```

If UQE is not installed, bridge functions return graceful no-ops or numpy stubs.

---

## Module Reference

| File | Function | Role |
|------|----------|------|
| `omnifold_uqe_bridge/entanglement.py` | `cross_branch_gradient(rho_i, rho_j, H_interaction=None)` | $\mathcal{G}_{\text{interact}} = \langle \Psi_i | \hat{H} | \Psi_j \rangle$ |
| `omnifold_uqe_bridge/er_epr_coupling.py` | `map_density_to_conductance(rho_i, rho_j, S_euclidean=1.0)` | $\rho \to \mathcal{G}_{ij}$ |
| `omnifold_uqe_bridge/README.md` | — | Package-level notes |

---

## Basic Usage

### Cross-branch entanglement gradient

```python
import numpy as np

try:
    from omnifold_uqe_bridge.entanglement import cross_branch_gradient
except ImportError:
    cross_branch_gradient = None

# 2-qubit density matrices (example)
rho_i = np.array([[0.5, 0, 0, 0.5], [0, 0, 0, 0], [0, 0, 0, 0], [0.5, 0, 0, 0.5]], dtype=complex)
rho_j = rho_i.copy()

if cross_branch_gradient is not None:
    H_int = np.kron(np.array([[0,1],[1,0]]), np.array([[0,1],[1,0]]))
    G_interact = cross_branch_gradient(rho_i, rho_j, H_interaction=H_int)
    print(f"Entanglement gradient: {G_interact}")
```

### Map to conductance

```python
from omnifold_uqe_bridge.er_epr_coupling import map_density_to_conductance

G_ij = map_density_to_conductance(rho_i, rho_j, S_euclidean=2.0)
# G_ij ≈ exp(-S_euclidean) * Tr(rho_i @ H @ rho_j)
```

### Attach to district graph

```python
from omnifold_core.superspace.district_graph import DistrictGraph
from omnifold_core.conductance.bridge_tensor import bridge_conductance

graph = DistrictGraph()
# ... add districts and choice events ...

# Set conductance from UQE
i, j = 0, 1
G_ij = map_density_to_conductance(rho_i, rho_j)
graph.set_conductance(i, j, float(G_ij))
```

---

## Master Equation Integration

Conductance feeds the district network evolution:

$$
\frac{d\mathbf{V}_i}{dt}
= \mathcal{F}(\mathbf{V}_i)
+ \sum_{j \in \mathcal{N}(i)} \mathcal{G}_{ij}\,
\left(\mathbf{V}_j - \mathbf{V}_i\right)
+ \text{branch kicks}
$$

```python
import numpy as np
from omnifold_core.conductance.bridge_tensor import conductance_matrix
from omnifold_core.conductance.master_equation import district_master_step

G = conductance_matrix(graph)  # includes UQE-derived G_ij
V = np.random.randn(graph.sector_count, 4)

V_next = district_master_step(V, F=lambda v: -0.1 * v, conductance_matrix=G, branch_kicks=None, dt=0.01)
```

Implementation: `omnifold_core/conductance/master_equation.py`

---

## Experiment Notebook

Full workflow: `experiments/06_er_epr_bridge_uqe.ipynb`

1. Simulate 5-choice event in `DistrictGraph`
2. Build UQE density matrices for branch pair $(i,j)$
3. Compute `cross_branch_gradient` and `map_density_to_conductance`
4. Run `district_master_step` with updated $\mathcal{G}_{ij}$
5. Compare echo amplitude to pure-GR null ($\mathcal{G}_{ij} = 0$)

---

## Fallback Without UQE

When `deepiri-uqe` is absent:

- `entanglement.py` uses Hermitian trace inner product stub
- `er_epr_coupling.py` returns $\mathcal{G}_{ij} = \exp(-S_{\text{Euclidean}}) \cdot |\mathrm{Tr}(\rho_i \rho_j)|$
- `falsification_flags.p3_gw_ringdown` remains `inconclusive`

Deterministic conductance without quantum simulation:

```python
from omnifold_core.conductance.bridge_tensor import bridge_conductance
import numpy as np

G_ij = bridge_conductance(
    S_euclidean=1.0,
    stream_i=np.array([1.0, 0, 0, 0]),
    stream_j=np.array([0.9, 0.1, 0, 0]),
    T_munu_coupling=0.01,
)
```

---

## Physical Interpretation

| UQE object | RBLE object |
|------------|-------------|
| Density matrix $\rho_k$ | Branch $k$ sector state |
| $\hat{H}_{\text{interaction}}$ | Cross-branch coupling |
| Entanglement entropy $S_E$ | Euclidean action proxy for bridge |
| Measurement outcome | Attenuated echo in parent district |

Branches born of the same parent choice event share non-zero $\mathcal{G}_{ij}$ — travelers in choice-born black holes occupy **mixed states** across sectors.

**Falsification:** Prediction P3 in [../theory/FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md) — correlated GW ringdown phases (future catalog adapter).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: deepiri_uqe` | Run `poetry install -E uqe`; check path in pyproject.toml |
| $\mathcal{G}_{ij} < 0$ | Bridge tensor clips to 0 in `bridge_tensor.py` |
| Conductance matrix not symmetric | Use $(G + G^T)/2$ for undirected approximation |
| Dimension mismatch | Ensure $\rho$ dimension matches branch Hilbert space |

---

## Related

- [getting_started.md](./getting_started.md)
- [running_simulations.md](./running_simulations.md)
- [../theory/SUPERSPACE_BRANCHING.md](../theory/SUPERSPACE_BRANCHING.md)
- [../theory/FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md) — Prediction P3
