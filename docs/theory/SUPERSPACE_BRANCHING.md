# Superspace Branching

Mathematics of the **district graph**, **Wheeler–DeWitt generator**, and **branching Langevin** dynamics — the superspace layer that turns choice events into new universe sectors.

**Master equations:** Equations 3, 4, 7 in [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md). **Implementation:** `src/polomni/core/superspace/`.

---

## Conceptual Model

RBLE replaces abstract many-worlds branching with a **topological network multiverse**:

- **Nodes** = spatial districts (sectors with local laws)
- **Edges** = one-way black-hole portals (choice-born graviton wells)
- **Superspace** = space of all 3-geometries $h_{ij}$ and matter fields $\phi$
- **Choice events** = discrete bifurcations that spawn $N$ child districts and inject stream momentum into $\Psi[h,\phi]$

```
                    ┌──► District 1 (Choice A)
                    ├──► District 2 (Choice B)
Parent District 0 ──┼──► District 3 (Choice C)
                    ├──► District 4 (Choice D)
                    └──► District 5 (Choice E)
                         │
                    each edge: black_hole_at, conductance G_ij
```

---

## District Graph

### Mathematical definition

Let $\mathcal{G}_{\text{district}} = (V, E)$ be a **directed acyclic graph**:

- $v_i \in V$ carries attributes $(M_i, g_i^{\text{local}}, \mathbf{x}_i, \Lambda_i)$
  - $M_i$ — district mass scale
  - $g_i^{\text{local}}$ — local gravitational constant / law vector
  - $\mathbf{x}_i$ — coordinate embedding
  - $\Lambda_i = \Lambda(W_i, K_i)$ — landscape vacuum at district
- $e_{ij} \in E$ carries $(\mathbf{bh}_{ij}, \mathcal{G}_{ij})$
  - $\mathbf{bh}_{ij}$ — black hole coordinate in parent sector
  - $\mathcal{G}_{ij}$ — ER=EPR conductance

### Choice event operator

When parent sector $p$ undergoes $N$-choice event at time $t_c$:

$$
\{v_p\} \xrightarrow{\text{Choice}(N)} \{v_{c_1}, \ldots, v_{c_N}\}
$$

Each child $c_k$ receives:

$$
g_{c_k}^{\text{local}} = g_p^{\text{local}} + \delta g_k, \quad
\delta g_k \sim \mathcal{N}(0, \sigma_g^2 \ln N)
$$

and edge metadata $\mathbf{bh}_{p,c_k}$ sampled in parent coordinates.

### Branch weights

Log-odds choice vector $\mathbf{C}_{\text{choice}}$ maps to probabilities:

$$
p_k = \frac{\exp(C_k)}{\sum_{j=1}^{N} \exp(C_j)}
\qquad\text{(softmax)}
$$

**Code:**

- `superspace/district_graph.py::DistrictGraph`
  - `add_district(mass, law_of_gravity, coordinate, lambda_vacuum)`
  - `trigger_choice_event(parent_sector, num_choices) -> list[StreamPacket]`
  - `get_conductance(i, j)`, `set_conductance(i, j, value)`
  - `to_dict()` / `from_dict()` serialization

---

## Branch Operator

### Vectorized spawning

The branching operator $\mathcal{B}_k$ acts on unified state $\mathbf{\Psi}$:

$$
\mathbf{\Psi}_k = \mathcal{B}_k(\mathbf{\Psi}, N)
= \mathcal{P}_k \mathbf{\Psi} + \delta \mathbf{\Psi}_k
$$

where $\mathcal{P}_k$ is a projection onto branch subspace and $\delta \mathbf{\Psi}_k$ mutates $\mathbf{\Lambda}_{\text{laws}}$ sector.

### PDE form with delta kick

$$
\frac{\partial \mathbf{\Psi}}{\partial t}
= \mathcal{F}(\mathbf{\Psi}, \nabla \mathbf{\Psi})
+ \sum_{k=1}^{N} \mathcal{B}_k(\mathbf{C})\, \delta(t - t_c)
$$

**Code:**

- `superspace/branch_operator.py::BranchOperator`
  - `B_k(psi, k, num_choices)`
  - `compute_branch_weights(choice_vector, num_choices)`
  - `split_state_vector(unified_state, num_choices) -> list[UnifiedStateVector]`

---

## Wheeler–DeWitt Generator

### Standard WDW (closed)

$$
\hat{H}_{\text{WDW}} \Psi[h_{ij}, \phi] = 0
$$

$$
\hat{H}_{\text{WDW}} =
-16\pi G \hbar^2 G_{ijkl}\frac{\delta^2}{\delta h_{ij}\,\delta h_{kl}}
- \frac{\sqrt{h}}{16\pi G}\left(R^{(3)} - 2\Lambda(W,K)\right)
+ \hat{H}_{\text{matter}}
$$

### RBLE generator form (stream injection)

$$
\hat{H}_{\text{WDW}} \Psi
= \sum_{k=1}^{N} \delta(\mathbf{p}_k - \Phi_{\text{stream}}^{(k)})
$$

Each delta **localizes** $\Psi$ into a new wavepacket peak — a child universe in superspace.

### Discrete approximation

On mini-superspace with scale factor $a$ and inflaton $\phi$:

$$
\Psi_k(a, \phi) = \mathcal{N}_k \exp\!\left(
-\frac{(a - a_k)^2}{2\sigma_a^2}
-\frac{(\phi - \phi_k)^2}{2\sigma_\phi^2}
\right)
$$

with centers seeded from stream:

$$
\mathbf{p}_k \approx \Phi_{\text{stream}}^{(k)}, \quad
\Delta g_k = \epsilon_k \|\Phi_{\text{stream}}^{(k)}\|
$$

**Code:**

- `superspace/wdw_generator.py::WDWGenerator`
  - `inject_stream(packet: StreamPacket, parent_state) -> list[Wavepacket]`
  - `spawn_wavepackets(num_choices, phi_stream)`
- `Wavepacket` model: `branch_id`, `metric_mutation`, `momentum_vector`, `stream_residual`

### Wavepacket normalization

$$
\sum_{k=1}^{N} p_k \int |\Psi_k|^2\, d\mu_{\mathfrak{S}} = 1
$$

enforced by branch weights $p_k$ from `BranchOperator`.

---

## Branching Langevin Dynamics

### Equation of motion

Particle momentum $\mathbf{p}$ in graviton well with $N$-way choice at $t_c$:

$$
d\mathbf{p}_k
= -\nabla \mathcal{V}_{\text{graviton}}(\mathbf{x})\, dt
+ \sum_{j=1}^{N} \mathcal{B}_j(\mathbf{\Psi})\, \delta(t - t_c)\, dt
+ \sigma\, d\mathbf{W}_t
$$

### Continuity across horizon

Integrated over horizon (links to Equation 4):

$$
\oint_{\mathcal{H}} \left(R_{\mu\nu} I_{(N)}^{\mu\nu}\right) d\Omega
= \sum_{k=1}^{N} \int_{t_0}^{t_f}
\left\|\frac{d\mathbf{p}_k}{dt}\right\|_{\mathbf{g}_k}^2 dt
$$

Left: geometric price of doorway. Right: kinetic energy across branches.

**Code:**

- `superspace/particle_langevin.py::BranchingLangevinEvolver`
  - `step(p, x, dt, grad_V, num_choices, t_choice)`
  - `evolve_trajectory(initial_p, initial_x, t_span, choice_times, num_choices_each)`

---

## Master Equation on Graph (Coupled Districts)

District spectrum vectors evolve with ER conductance:

$$
\frac{d\mathbf{V}_i}{dt}
= \mathcal{F}(\mathbf{V}_i)
+ \sum_{j \in \mathcal{N}(i)} \mathcal{G}_{ij}\,
\left(\mathbf{V}_j - \mathbf{V}_i\right)
+ \sum_{k=1}^{N_i} \mathcal{B}_k(\mathbf{C})\,
\delta(t - t_c)\, \mathbf{V}_i^{(k)}
$$

**Code:** `conductance/master_equation.py::district_master_step`

---

## Full Branching Workflow

```
1. DistrictGraph.trigger_choice_event(parent, N)
      │
      ├─► BranchOperator.split_state_vector → N UnifiedStateVectors
      ├─► information_tensor_N(N, ...) → I_μν
      │
2. RadonVacuumPipeline (per child or parent aggregate)
      │
      └─► StreamPacket with phi_stream, information_trace
      │
3. WDWGenerator.inject_stream(packet)
      │
      └─► list[Wavepacket] with metric mutations
      │
4. BranchingLangevinEvolver.evolve_trajectory(...)
      │
      └─► p_k(t) histories for continuity check
      │
5. conductance_matrix + district_master_step
      │
      └─► updated V_i on graph
```

---

## Serialization and Reproducibility

`DistrictGraph.to_dict()` preserves:

- Node attributes: `mass`, `law_of_gravity`, `coordinate`, `lambda_vacuum`
- Edge attributes: `black_hole_at`, `conductance`
- Global `sector_count`

Round-trip `from_dict` must reproduce identical adjacency and weights for regression tests.

---

## Graph Invariants

| Invariant | Enforcement |
|-----------|-------------|
| DAG (no cycles) | NetworkX `is_directed_acyclic_graph` |
| $\sum_k p_k = 1$ | Softmax in `BranchOperator` |
| Stream closure | `conservation.py` on each `StreamPacket` |
| $\mathcal{G}_{ij} \geq 0$ | Clipped in `bridge_tensor.py` |

---

## Related documents

- [RADON_VACUUM_PIPELINE.md](./RADON_VACUUM_PIPELINE.md) — produces `StreamPacket`
- [STRING_LANDSCAPE_COUPLING.md](./STRING_LANDSCAPE_COUPLING.md) — $\Lambda_i$ per district
- [NOTATION.md](./NOTATION.md) — symbol table
- [../guides/running_simulations.md](../guides/running_simulations.md)
