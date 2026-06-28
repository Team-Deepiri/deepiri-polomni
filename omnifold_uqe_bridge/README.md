# omnifold_uqe_bridge

Optional integration with [deepiri-uqe](https://github.com/deepiri/deepiri-uqe) for
quantum entanglement layers in the ER=EPR conductance bridge (RBLE Eq. 7).

## Install

From the `deepiri-omnifold` repo root, with a sibling checkout of `deepiri-uqe`:

```bash
poetry install --with uqe
```

Or add the path dependency manually:

```bash
poetry add ../deepiri-uqe --group uqe
```

## Usage

Without UQE installed, bridge functions use NumPy fallbacks:

```python
import numpy as np
from omnifold_uqe_bridge import cross_branch_gradient, map_density_to_conductance

rho_a = np.eye(2) / 2
rho_b = np.array([[0.7, 0], [0, 0.3]])
G = map_density_to_conductance([rho_a, rho_b])
```

With UQE installed, `cross_branch_gradient` may delegate to
`quantum_core.metrics.entanglement` when an interaction Hamiltonian is supplied.

## Modules

| Module | Purpose |
|--------|---------|
| `entanglement.py` | Cross-branch gradient from density matrices |
| `er_epr_coupling.py` | Map densities → conductance tensor G_ij |

See `docs/guides/uqe_bridge.md` (when present) for notebook `experiments/06_er_epr_bridge_uqe.ipynb`.
