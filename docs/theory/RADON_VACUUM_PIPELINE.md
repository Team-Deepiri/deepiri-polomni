# Radon Vacuum Pipeline

Step-by-step mathematics of the **encapsulate → rotate → stream** pipeline that compresses district field data through a graviton well horizon and produces a conserved `StreamPacket`.

**Master equation:** Equation 4 closure and stream definition in [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md). **Implementation:** `omnifold_core/radon/`.

---

## Pipeline Overview

```
District field Ψ(x)  on Ω ⊂ R³
        │
        ▼  (1) ENCAPSULATE — Radon bubble scan
   R[Ψ](p, ξ)  holographic sheet
        │
        ▼  (2) ROTATE — SO(3) gauge alignment
   M(θ,φ,ψ) · R[Ψ]  →  particle spectrum V_p
        │
        ▼  (3) STREAM — graviton vacuum flux
   Φ_stream  through H
        │
        ▼  (4) CONSERVE — closure check
   StreamPacket  (iff ∮ Φ dA = Tr(I²))
```

**Class:** `omnifold_core/radon/vacuum_stream.py::RadonVacuumPipeline`

| Stage | Method | Module |
|-------|--------|--------|
| Encapsulate | `encapsulate_and_scan()` | `transform_r3.py` |
| Rotate | `rotate_particle_properties()` | `so3_rotation.py` |
| Stream | `stream_to_vacuum()` | `vacuum_stream.py` + `conservation.py` |

---

## Stage 1: Encapsulate — Radon Bubble Scan

### Continuous definition

The Radon transform integrates the district unified field $\mathbf{\Psi}(\mathbf{x})$ over hyperplanes orthogonal to direction $\boldsymbol{\xi}$:

$$
\mathcal{R}[\mathbf{\Psi}](p, \boldsymbol{\xi})
= \int_{\mathbb{R}^3} \mathbf{\Psi}(\mathbf{x})\,
\delta(\mathbf{x}\cdot\boldsymbol{\xi} - p)\, d^3x
$$

where $\boldsymbol{\xi} \in S^2$ is a unit slice direction and $p \in \mathbb{R}$ is signed plane offset from origin.

### Physical interpretation

The **Radon isolation bubble** $\mathcal{R}_B$ is a spherical bounding manifold around district $\Omega$. Scanning at all $(p, \boldsymbol{\xi})$ produces a complete tomographic profile — a **holographic data sheet** encoding mass, momentum, law-constant, and choice sectors of $\mathbf{\Psi}$ without storing full 3D chaos.

### Discrete implementation

On a uniform grid $\mathbf{x}_{ijk}$ with spacing $\Delta x$:

$$
\mathcal{R}[\mathbf{\Psi}](p, \boldsymbol{\xi})
\approx \Delta x^3 \sum_{ijk}
\mathbf{\Psi}_{ijk}\,
\mathcal{W}(\mathbf{x}_{ijk}\cdot\boldsymbol{\xi} - p;\, \sigma)
$$

where $\mathcal{W}$ is a narrow Gaussian approximating $\delta$ (default $\sigma = \Delta x / \sqrt{2\pi}$).

**Code:** `omnifold_core/radon/transform_r3.py::radon_transform_r3(psi_field, xi, p)`

### Input / output contract

| Input | Shape | Description |
|-------|-------|-------------|
| `psi_field` | `(Nx, Ny, Nz, C)` | District field; $C$ = components of $\mathbf{\Psi}$ |
| `xi` | `(3,)` | Unit slice direction |
| `p` | scalar | Plane offset |

| Output | Shape | Description |
|--------|-------|-------------|
| `radon_sheet` | `(N_p, C)` or `(C,)` | Integrated profile along slice family |

---

## Stage 2: Rotate — SO(3) Particle Property Extraction

### Continuous definition

Apply rotation matrix $\mathbf{M}(\theta, \phi, \psi) \in SO(3)$ (Euler angles) to the Radon sheet:

$$
\mathbf{\Psi}_{\text{rotated}}
= \mathbf{M}(\theta, \phi, \psi) \cdot \mathcal{R}[\mathbf{\Psi}](p, \boldsymbol{\xi})
$$

Particle spectrum extraction projects onto eigenchannels:

$$
\mathbf{V}_p = \mathrm{ExtractSpectrum}(\mathbf{\Psi}_{\text{rotated}})
= \left[\, m,\; q,\; s,\; \lambda_{\text{local}} \,\right]^T
$$

(mass proxy, charge proxy, spin alignment, local law constant).

### Physical interpretation

Quantum numbers transform under $SO(3)$ and $SU(2)$. Rotation **filters** background noise: fermionic vs. bosonic content separates by response to $\mathbf{M}$. The output $\mathbf{V}_p$ is the **distilled district DNA** — what the parent universe passes to children.

### Discrete implementation

**Code:**

- `omnifold_core/radon/so3_rotation.py::rotation_matrix_euler(theta, phi, psi)`
- `rotate_radon_bubble(data, angles)` — applies $\mathbf{M}$ to Radon coefficients
- `extract_particle_spectrum(rotated_data)` — collapses to $\mathbf{V}_p$

For multi-component Radon data, rotation acts on the leading spatial channel block; spectrum extraction uses SVD energy per channel:

$$
V_{p,c} = \sqrt{\sum_i \sigma_i^2(\text{channel } c)}
$$

---

## Stage 3: Stream — Graviton Vacuum Flux

### Continuous definition

The rotated data converts to a stream through horizon $\mathcal{H}$:

$$
\Phi_{\text{stream}}
= \iint_{\mathcal{H}}
\left(
\mathbf{\Psi}_{\text{rotated}} \otimes \mathcal{A}_{\text{vacuum}}
\right) \cdot d\mathbf{A}
$$

where $\mathcal{A}_{\text{vacuum}}$ is the graviton vacuum vector potential (directional pull into the well).

### Vacuum activation

Near the horizon, gravitational time dilation stabilizes the stream. Code uses a saturating activation:

$$
\Phi_{\text{stream}} \mapsto \tanh(\mathbf{\Psi}_{\text{rotated}}) \cdot \frac{c}{\|\Lambda(W,K)\| + \epsilon}
$$

scaling by local landscape vacuum energy from `landscape/vacuum_energy.py::lambda_vacuum`.

### Stream flux magnitude

$$
\|\Phi_{\text{stream}}\|_{\mathcal{H}}
= \oint_{\mathcal{H}} |\Phi_{\text{stream}}|\, dA
\approx |\Phi_{\text{stream}}| \cdot A_{\mathcal{H}}
$$

**Code:** `omnifold_core/conservation.py::stream_flux_integral(phi_stream, horizon_area)`

### Output: StreamPacket

`omnifold_core/state/stream_packet.py::StreamPacket` fields:

| Field | Math object |
|-------|-------------|
| `phi_stream` | $\Phi_{\text{stream}}$ vector |
| `information_trace` | $\mathrm{Tr}(I^2)$ target |
| `branch_weights` | $p_k$ from parent choice |
| `num_choices` | $N$ |
| `district_id`, `parent_id` | Graph indices |

---

## Stage 4: Conservation Closure

### Closure identity

From Equation 4 (integrated):

$$
\oint_{\mathcal{H}} \Phi_{\text{stream}} \cdot dA
= \mathrm{Tr}\!\left(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu}\right)
$$

### Information tensor at stream time

For $N$ choices with entropy gradient $\mathbf{s}$:

$$
I_{\mu\nu}^{(N)} = \xi_I \,\ln(N)\, \left(
\mathbf{s}_\mu \mathbf{s}_\nu - \frac{1}{4} g_{\mu\nu} \mathbf{s}^2
\right)
$$

**Code:** `gravity/information_tensor.py::information_tensor_N`, `trace_I_squared`

### Enforcement

```python
# omnifold_core/conservation.py
enforce_stream_entropy_closure(phi_stream, information_tensor_trace) -> bool
```

Raises `ConservationViolationError` if relative error exceeds tolerance (default $10^{-6}$):

$$
\left|
\frac{\|\Phi_{\text{stream}}\| \cdot A_{\mathcal{H}} - \mathrm{Tr}(I^2)}
{\mathrm{Tr}(I^2)}
\right| > \tau
$$

---

## End-to-End Pipeline Class

```python
from omnifold_core.radon.vacuum_stream import RadonVacuumPipeline

pipeline = RadonVacuumPipeline(horizon_area=4 * np.pi * r_s**2)
sheet = pipeline.encapsulate_and_scan(district_psi_field)
rotated = pipeline.rotate_particle_properties(sheet, angles=(theta, phi, psi))
packet = pipeline.stream_to_vacuum(rotated, num_choices=N, district_id=k)
```

### Collision policy (two districts, one vacuum)

When districts $i$ and $j$ stream simultaneously into overlapping horizons, streams **superpose** before conservation check:

$$
\Phi_{\text{total}} = \Phi_{\text{stream}}^{(i)} + \Phi_{\text{stream}}^{(j)}
$$

Closure requires joint information trace:

$$
\mathrm{Tr}(I^2)_{\text{total}} = \mathrm{Tr}(I^2)_i + \mathrm{Tr}(I^2)_j
$$

Failure indicates **cosmic data crash** — simulation should abort or split vacuum channels. Future: `conductance/bridge_tensor.py` routes concurrent streams.

---

## Spherical Extension (CMB)

The $\mathbb{R}^3$ pipeline generalizes to $S^2$ for sky maps:

$$
\mathcal{R}_{S^2}[f](\hat{\mathbf{n}}, \eta)
= \int_{\gamma(\hat{\mathbf{n}},\eta)} f\, dl
$$

See [CMB_OBSERVATORY_MATH.md](./CMB_OBSERVATORY_MATH.md) and `radon/transform_s2.py`.

---

## Numerical Invariants (Tests)

| Invariant | Test location |
|-----------|---------------|
| $\|\boldsymbol{\xi}\| = 1$ | `tests/unit/test_radon_transform_r3.py` |
| $\det \mathbf{M} = 1$ | `tests/unit/test_so3_rotation.py` |
| Closure error $< \tau$ | `tests/unit/test_conservation.py` |
| End-to-end packet valid | `tests/integration/test_full_loop.py` |

---

## Related documents

- [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md) — Equations 2, 4, 6
- [SUPERSPACE_BRANCHING.md](./SUPERSPACE_BRANCHING.md) — consumer of `StreamPacket`
- [STRING_LANDSCAPE_COUPLING.md](./STRING_LANDSCAPE_COUPLING.md) — $\Lambda(W,K)$ stream scaling
- [../guides/running_simulations.md](../guides/running_simulations.md) — CLI usage
