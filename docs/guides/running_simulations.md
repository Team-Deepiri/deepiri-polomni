# Running Simulations

Guide to running **RBLE district simulations** — choice events, Radon vacuum streaming, Wheeler–DeWitt spawning, and inflation updates.

**Theory:** [../theory/SUPERSPACE_BRANCHING.md](../theory/SUPERSPACE_BRANCHING.md), [../theory/RADON_VACUUM_PIPELINE.md](../theory/RADON_VACUUM_PIPELINE.md)

---

## CLI Simulation

```bash
poetry run omnifold simulate --choices 5 --districts 1 --seed 42
```

| Flag | Default | Description |
|------|---------|-------------|
| `--choices` | `5` | Branches per choice event ($N$) |
| `--districts` | `1` | Initial district count |
| `--seed` | `None` | RNG seed for reproducibility |
| `--output` | stdout | JSON graph + stream packets |

Example output structure:

```json
{
  "graph": { "nodes": [...], "edges": [...] },
  "stream_packets": [
    {
      "district_id": 1,
      "parent_id": 0,
      "num_choices": 5,
      "phi_stream": [0.1, 0.2, 0.0, 0.0],
      "information_trace": 0.05,
      "branch_weights": [0.22, 0.18, 0.21, 0.19, 0.20]
    }
  ]
}
```

---

## Python API — Full Loop

### 1. Build district graph

```python
from omnifold_core.superspace.district_graph import DistrictGraph

graph = DistrictGraph()
root = graph.add_district(
    mass=100.0,
    law_of_gravity=9.81,
    coordinate=(0.0, 0.0, 0.0),
    lambda_vacuum=-1e-120,  # landscape Λ(W,K)
)
```

### 2. Trigger choice event

```python
packets = graph.trigger_choice_event(parent_sector=root, num_choices=5)

assert abs(sum(p.branch_weights[0] for p in packets) - 1.0) < 1e-6  # weights sum to 1
```

Each child district receives mutated `law_of_gravity` and a `black_hole_at` edge coordinate.

### 3. Radon vacuum pipeline

```python
import numpy as np
from omnifold_core.radon.vacuum_stream import RadonVacuumPipeline

# District field Ψ on 32³ grid, C=4 components
psi_field = np.random.randn(32, 32, 32, 4)

pipeline = RadonVacuumPipeline(horizon_area=4.0)
sheet = pipeline.encapsulate_and_scan(psi_field)
rotated = pipeline.rotate_particle_properties(sheet, angles=(0.785, 0.0, 0.0))
packet = pipeline.stream_to_vacuum(
    rotated,
    num_choices=5,
    district_id=1,
    parent_id=root,
)
```

Pipeline implements:

$$
\mathcal{R}[\mathbf{\Psi}] \;\to\; \mathbf{M}\cdot\mathcal{R}[\mathbf{\Psi}] \;\to\; \Phi_{\text{stream}}
$$

### 4. Conservation check

```python
from omnifold_core.conservation import enforce_stream_entropy_closure
from omnifold_core.gravity.information_tensor import information_tensor_N, trace_I_squared

I = information_tensor_N(num_choices=5, entropy_gradient=np.array([1.0, 0, 0, 0]))
tr_I2 = trace_I_squared(I)

assert enforce_stream_entropy_closure(
    packet.phi_stream,
    packet.information_trace,
    horizon_area=pipeline.horizon_area,
)
```

### 5. Wheeler–DeWitt wavepacket spawn

```python
from omnifold_core.superspace.wdw_generator import WDWGenerator

wdw = WDWGenerator()
wavepackets = wdw.inject_stream(packet, parent_state=None)

assert len(wavepackets) == 5
for wp in wavepackets:
    assert wp.metric_mutation is not None
    assert wp.momentum_vector is not None
```

Discrete form of:

$$
\hat{H}_{\text{WDW}} \Psi = \sum_k \delta(\mathbf{p}_k - \Phi_{\text{stream}}^{(k)})
$$

### 6. Directed Fokker–Planck step

```python
import numpy as np
from omnifold_core.inflation.fokker_planck import fokker_planck_step, radon_modified_D_eff

phi_grid = np.linspace(-2, 2, 100)
P = np.exp(-phi_grid**2)  # normalized PDF
P /= np.trapz(P, phi_grid)

V = lambda phi: 0.5 * phi**2  # quadratic inflaton
H = 0.7  # Hubble parameter

stream_fluxes = [np.linalg.norm(packet.phi_stream)]
D_eff = radon_modified_D_eff(H, stream_fluxes, lambda_coupling=0.1)

P_next = fokker_planck_step(P, phi_grid, V, H, dt=0.01, D_eff=D_eff)
```

### 7. Conductance network step

```python
import numpy as np
from omnifold_core.conductance.bridge_tensor import conductance_matrix
from omnifold_core.conductance.master_equation import district_master_step

G = conductance_matrix(graph)
V = np.random.randn(graph.sector_count, 4)  # district spectrum vectors

V_next = district_master_step(
    V, F=lambda v: -0.1 * v,
    conductance_matrix=G,
    branch_kicks=None,
    dt=0.01,
)
```

---

## Branching Langevin Trajectories

```python
from omnifold_core.superspace.particle_langevin import BranchingLangevinEvolver

evolver = BranchingLangevinEvolver(sigma=0.1)
grad_V = lambda x: x  # harmonic well

p, x = evolver.evolve_trajectory(
    initial_p=np.array([1.0, 0.0, 0.0]),
    initial_x=np.array([0.0, 0.0, 0.0]),
    t_span=(0.0, 2.0),
    choice_times=[1.0],
    num_choices_each=[5],
    grad_V=grad_V,
    dt=0.001,
)
```

Equation:

$$
d\mathbf{p}_k = -\nabla \mathcal{V}_{\text{graviton}}\, dt
+ \sum_j \mathcal{B}_j(\mathbf{\Psi})\, \delta(t-t_c)\, dt
+ \sigma\, d\mathbf{W}_t
$$

---

## Landscape Parameters

Set string landscape at district creation:

```python
from omnifold_core.landscape.superpotential import superpotential_W
from omnifold_core.landscape.vacuum_energy import lambda_vacuum
from omnifold_core.landscape.kahler import kahler_total

W = superpotential_W([1, 0, -1, 2])
K = kahler_total(T=1.0, T_bar=1.0, I_trace=0.01, phi_stream_flux=0.001, beta=1.0, gamma=0.5)
Lambda = lambda_vacuum(W, K)
```

See [../theory/STRING_LANDSCAPE_COUPLING.md](../theory/STRING_LANDSCAPE_COUPLING.md).

---

## Visualization

```python
from visualization.district_graph_viz import plot_district_graph
from visualization.stream_pipeline_viz import plot_stream_pipeline

plot_district_graph(graph.galaxy_graph)
plot_stream_pipeline(stages={
    "radon": sheet,
    "rotated": rotated,
    "stream": packet.phi_stream,
})
```

---

## Integration Test

The canonical regression test:

```bash
poetry run pytest tests/integration/test_full_loop.py -v
```

Validates: choice → stream → conservation → WDW spawn → $D_{\text{eff}}$ update.

---

## Parameter Tuning

| Parameter | Module | Effect |
|-----------|--------|--------|
| $\xi$ | `gravity/field_equations.py` | Choice–gravity coupling |
| $\lambda$ | `inflation/fokker_planck.py` | Stream–diffusion coupling |
| $\beta, \gamma$ | `landscape/kahler.py` | Moduli stabilization |
| `horizon_area` | `radon/vacuum_stream.py` | Closure normalization |
| `sigma` | `particle_langevin.py` | Quantum noise amplitude |

---

## Related

- [getting_started.md](./getting_started.md)
- [cmb_data_pipeline.md](./cmb_data_pipeline.md) — observatory after simulation
- [../theory/RBLE_MASTER_EQUATIONS.md](../theory/RBLE_MASTER_EQUATIONS.md)
