# polomni.bridge

Optional cross-sector coupling utilities (ER=EPR conductance, entanglement gradients).

**Not coupled to external quantum engines by default.** This package provides NumPy-native
stubs so the RBLE district graph and master equation can run standalone. Future quantum
integrations will plug in here without changing `polomni.core`.

## Modules

| Module | Purpose |
|--------|---------|
| `entanglement.py` | `cross_branch_gradient` — cross-sector correlation proxy |
| `er_epr_coupling.py` | `map_density_to_conductance` — density matrix → G_ij |

## Usage

```python
from polomni.bridge.er_epr_coupling import map_density_to_conductance
import numpy as np

rho_a = np.eye(4) / 4
rho_b = np.eye(4) / 4
g = map_density_to_conductance(rho_a, rho_b)
```
