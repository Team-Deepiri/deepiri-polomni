# RBLE Master Equations

**Radon-Bifurcated Landscape Engine (RBLE)** — canonical equation chain for `deepiri-polomni`.

This document is the single source of truth for the eight connected field equations that close the multiverse loop: string landscape → inflation → choice → horizon stream → superspace birth → CMB scar → ER bridge → moduli stabilization. Each equation maps to a concrete module under `src/polomni/core/` or `src/polomni/observatory/`.

**Related docs:** [VARIATIONAL_PRINCIPLE.md](./VARIATIONAL_PRINCIPLE.md) · [NOTATION.md](./NOTATION.md) · [FALSIFICATION_CRITERIA.md](./FALSIFICATION_CRITERIA.md)

---

## Equation Chain Overview

| # | Name | Primary module |
|---|------|----------------|
| 1 | Informational-String Field Metric | `src/polomni/core/gravity/field_equations.py` |
| 2 | Radon-Rotated Fokker-Planck (compact) | `src/polomni/core/inflation/fokker_planck.py` |
| 3 | Topological Wheeler-DeWitt Bifurcation Closure | `src/polomni/core/superspace/wdw_generator.py` |
| 4 | Choice Entropy Continuity Law | `src/polomni/core/conservation.py` |
| 5 | Radon-Modulated Fokker-Planck (full form) | `src/polomni/core/inflation/drift_diffusion.py` |
| 6 | Spherical Radon Scar on $S^2$ (HEALPix) | `src/polomni/core/radon/transform_s2.py` |
| 7 | ER=EPR Bridge Conductance Tensor | `src/polomni/core/conductance/bridge_tensor.py` |
| 8 | Kähler Stabilization as Dynamic Boundary Condition | `src/polomni/core/landscape/kahler.py` |

---

## 1. Informational-String Field Metric

### Statement

Modified Einstein field equations with landscape-derived cosmological constant $\Lambda(W,K)$ and $N$-choice informational stress $I_{\mu\nu}^{(N)}$:

$$
R_{\mu\nu} - \frac{1}{2} R g_{\mu\nu} + \Lambda(W,K)\, g_{\mu\nu}
= \frac{8\pi G}{c^4}\left(T_{\mu\nu} + \xi\, I_{\mu\nu}^{(N)}\right)
$$

where the string-landscape vacuum energy density is

$$
\Lambda(W,K) = \langle V_D \rangle
= e^{K/M_P^2}\left(K^{I\bar{J}} D_I W \,\overline{D_J W} - \frac{3}{M_P^2}|W|^2\right)
+ \sum_{\text{uplift}} V_{\text{uplift}}
$$

and $D_I W = \partial_I W + \frac{1}{M_P^2} W \partial_I K$ is the Kähler covariant derivative.

### Term definitions

| Symbol | Definition |
|--------|------------|
| $R_{\mu\nu}, R, g_{\mu\nu}$ | Ricci tensor, scalar curvature, spacetime metric |
| $T_{\mu\nu}$ | Standard stress-energy (matter, radiation, inflaton) |
| $I_{\mu\nu}^{(N)}$ | Informational stress from an $N$-way choice bifurcation |
| $\xi$ | Informational–gravitational coupling constant |
| $W, K$ | Superpotential and Kähler potential on Calabi–Yau moduli |
| $M_P$ | Reduced Planck mass |

### Physical meaning

When a district undergoes an $N$-choice event, the local information entropy gradient produces a spike in $I_{\mu\nu}^{(N)} \propto \ln N$. If $\xi \,\mathrm{Tr}(I^2)$ exceeds the stabilizing pressure from $\Lambda(W,K)$, the metric undergoes localized collapse — a **graviton vacuum well** (choice-born black hole). The cosmological constant is not a fixed constant; it **competes** with choice-induced stress at each bifurcation node.

### Code connection

- **`src/polomni/core/gravity/information_tensor.py`** — `information_tensor_N(num_choices, entropy_gradient)` builds $I_{\mu\nu}^{(N)}$; `trace_I_squared()` computes $\mathrm{Tr}(I^2)$.
- **`src/polomni/core/gravity/field_equations.py`** — `modified_field_residual(g, T, I, Lambda)` evaluates the LHS − RHS residual; `einstein_rhs(T_munu, I_munu, xi)` assembles the source.
- **`src/polomni/core/landscape/vacuum_energy.py`** — `lambda_vacuum(W, K, M_P)` evaluates $\Lambda(W,K)$.
- **`src/polomni/core/gravity/schwarzschild_choice.py`** — `schwarzschild_metric_with_choice(M, I_choice, gamma, r_grid)` gives the $I_{\text{choice}}$-injected Schwarzschild limit for district-scale wells.

---

## 2. Radon-Rotated Fokker-Planck (Compact Form)

### Statement

Eternal-inflation probability density $P(\phi,t)$ with diffusion coefficient modulated by Radon-rotated district flux through horizon $\mathcal{H}$:

$$
\frac{\partial P(\phi,t)}{\partial t}
= \frac{\partial}{\partial\phi}\left[\frac{V'(\phi)}{3H(\phi)}\, P(\phi,t)\right]
+ D_{\text{eff}}^{\text{(compact)}}(\phi,t)\,
\frac{\partial^2 P(\phi,t)}{\partial \phi^2}
$$

with

$$
D_{\text{eff}}^{\text{(compact)}}(\phi,t)
= \iint_{\mathcal{H}}
\left\|\mathbf{M}(\theta,\phi_{\text{ang}})\cdot \mathcal{R}[\mathbf{\Psi}]\right\|_{\mathbf{g}_k}^{2}\, dA
$$

(The standard quantum term $H^3/(8\pi^2)$ is retained in the full form — Equation 5.)

### Term definitions

| Symbol | Definition |
|--------|------------|
| $P(\phi,t)$ | Probability density of inflaton field value $\phi$ at time $t$ |
| $V(\phi), V'(\phi)$ | Inflaton potential and its derivative |
| $H(\phi)$ | Hubble parameter during slow roll |
| $\mathcal{R}[\mathbf{\Psi}]$ | Radon transform of district unified field $\mathbf{\Psi}$ |
| $\mathbf{M}(\theta,\phi_{\text{ang}})$ | $SO(3)$ rotation matrix for particle-property extraction |
| $\|\cdot\|_{\mathbf{g}_k}$ | Norm w.r.t. branch metric $\mathbf{g}_k$ |

### Physical meaning

In standard eternal inflation, quantum diffusion is **memoryless** and isotropic in field space. RBLE replaces part of the diffusion with a **parent-encoded** flux: districts that recently streamed Radon-compressed data through their horizons inject directed noise into neighboring inflationary patches. Pocket universes inherit statistical bias from parent particle spectra.

### Code connection

- **`src/polomni/core/inflation/fokker_planck.py`** — `fokker_planck_step(P, phi, V, H, dt, D_eff)` advances $P$ one timestep; `radon_modified_D_eff(H, stream_fluxes, lambda_coupling)` evaluates the compact diffusion modifier.
- **`src/polomni/core/radon/transform_r3.py`** — `radon_transform_r3(psi_field, xi, p)` implements $\mathcal{R}[\mathbf{\Psi}]$ on $\mathbb{R}^3$ grids.
- **`src/polomni/core/radon/so3_rotation.py`** — `rotation_matrix_euler`, `rotate_radon_bubble` apply $\mathbf{M}$.

---

## 3. Topological Wheeler-DeWitt Bifurcation Closure

### Statement

The Wheeler-DeWitt equation becomes a **dynamic generator** when Radon vacuum streams inject momentum into superspace:

$$
\left[
-16\pi G \hbar^2 G_{ijkl}\frac{\delta^2}{\delta h_{ij}\,\delta h_{kl}}
- \frac{\sqrt{h}}{16\pi G}\left(R^{(3)} - 2\Lambda(W,K)\right)
+ \hat{H}_{\text{matter}}
\right]\Psi[h_{ij},\phi]
= \sum_{k=1}^{N} \delta\!\left(\mathbf{p}_k - \Phi_{\text{stream}}^{(k)}\right)
$$

Standard quantum cosmology sets the RHS to zero (timeless closure). RBLE adds Dirac deltas that **force** the wave function of the universe to fracture into $N$ localized wavepackets when stream data arrives at the singularity.

### Term definitions

| Symbol | Definition |
|--------|------------|
| $\Psi[h_{ij},\phi]$ | Wave function of the universe over 3-metrics $h_{ij}$ and matter fields |
| $G_{ijkl}$ | DeWitt metric on superspace |
| $R^{(3)}$ | Intrinsic scalar curvature of spatial slice |
| $\Phi_{\text{stream}}^{(k)}$ | Momentum injection from branch $k$ vacuum stream |
| $\mathbf{p}_k$ | Superspace momentum conjugate to $h_{ij}$ for branch $k$ |

### Physical meaning

Each choice-born graviton well acts as a **mechanical trigger** in superspace. Streamed district data does not merely correlate with new universes — it **localizes** $\Psi$ into $N$ distinct peaks, each carrying mutated moduli and metric data from the parent Radon pipeline.

### Code connection

- **`src/polomni/core/superspace/wdw_generator.py`** — `WDWGenerator.inject_stream(packet, parent_state)` and `spawn_wavepackets(num_choices, phi_stream)` discretize the delta injection; returns `Wavepacket` models with `metric_mutation`, `momentum_vector`, `stream_residual`.
- **`src/polomni/core/state/stream_packet.py`** — `StreamPacket` carries `phi_stream`, `branch_weights`, `information_trace` consumed by the generator.
- **`src/polomni/core/superspace/particle_langevin.py`** — `BranchingLangevinEvolver` tracks $\mathbf{p}_k$ trajectories with delta kicks at $t_{\text{choice}}$.

---

## 4. Choice Entropy Continuity Law

### Statement

Information current conservation with log-odds sources at bifurcation points:

$$
\nabla_\mu J^\mu_{\text{choice}}
= \sum_{k=1}^{N} \delta^{(4)}(x - x_k)\,
\ln\!\left(\frac{p_k}{p_0}\right)
$$

Integrated over district $\Omega$ and linked to horizon flux:

$$
\int_\Omega \nabla_\mu J^\mu_{\text{choice}}\, d^4x
= \mathrm{Tr}\!\left(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu}\right)
= \oint_{\mathcal{H}} \Phi_{\text{stream}} \cdot dA
$$

### Term definitions

| Symbol | Definition |
|--------|------------|
| $J^\mu_{\text{choice}}$ | Information current (Fisher–Ruppeiner geometry) |
| $p_k$ | Branch weight after softmax of log-odds |
| $p_0$ | Reference (parent) branch probability |
| $\Phi_{\text{stream}}$ | Multiversal data stream through horizon $\mathcal{H}$ |

### Physical meaning

Choices gravitate through **entropy**, not rest mass. The continuity law is the **exact bridge** between abstract decision branching and measurable Radon vacuum flux. Violation of the integrated equality signals a non-physical simulation or numerical instability.

### Code connection

- **`src/polomni/core/conservation.py`** — `enforce_stream_entropy_closure(phi_stream, information_tensor_trace)` verifies $\oint \Phi\, dA = \mathrm{Tr}(I^2)$; `stream_flux_integral(phi_stream, horizon_area)`; `compute_information_trace(I_mu_nu)`; raises `ConservationViolationError` on failure.
- **`src/polomni/core/superspace/branch_operator.py`** — `compute_branch_weights(choice_vector, num_choices)` produces $p_k$ via softmax of log-odds.
- **`src/polomni/core/radon/vacuum_stream.py`** — `RadonVacuumPipeline.stream_to_vacuum()` returns `StreamPacket` satisfying closure when pipeline completes.

---

## 5. Radon-Modulated Fokker-Planck (Full Form)

### Statement

Complete Fokker-Planck equation with standard quantum diffusion plus district-weighted Radon flux sum:

$$
\frac{\partial P(\phi,t)}{\partial t}
= \frac{\partial}{\partial\phi}\left[\frac{V'(\phi)}{3H(\phi)}\, P\right]
+ D_{\text{eff}}(\phi,t)\,\frac{\partial^2 P}{\partial \phi^2}
$$

$$
D_{\text{eff}}(\phi,t)
= \frac{H(\phi)^3}{8\pi^2}
+ \lambda \sum_{k} w_k
\iint_{\mathcal{H}_k}
\left\|
\mathbf{M}_k(\theta,\phi_{\text{ang}})\cdot \mathcal{R}_k[\mathbf{\Psi}]
\right\|_{\mathbf{g}_k}^{2}\, dA
$$

### Term definitions

| Symbol | Definition |
|--------|------------|
| $H^3/(8\pi^2)$ | Standard eternal-inflation quantum diffusion coefficient |
| $\lambda$ | Coupling between stream flux and field-space diffusion |
| $w_k$ | District graph weight for sector $k$ |
| $\mathcal{H}_k$ | Horizon associated with district $k$ |

### Physical meaning

Equation 2 is the **single-horizon** limit. Equation 5 is the **network form**: inflation in any patch feels a superposition of stream histories from all districts in its causal neighborhood on the district DAG. This produces **spatially clustered** non-Gaussianity — a key falsifiable distinction from homogeneous $f_{\mathrm{NL}}$ in standard models.

### Code connection

- **`src/polomni/core/inflation/drift_diffusion.py`** — `classical_drift(V_prime, H)`, `quantum_diffusion(H)`, `directed_diffusion(stream_flux_integral)` assemble drift and diffusion terms separately.
- **`src/polomni/core/inflation/fokker_planck.py`** — full-step integration uses combined $D_{\text{eff}}$.
- **`src/polomni/core/superspace/district_graph.py`** — `DistrictGraph` provides district indices $k$ and causal adjacency for weighting $w_k$.

---

## 6. Spherical Radon Scar on $S^2$ (HEALPix)

### Statement

Geodesic Radon transform on the CMB sky sphere:

$$
\mathcal{R}_{S^2}[f](\hat{\mathbf{n}}, \eta)
= \int_{\gamma(\hat{\mathbf{n}},\,\eta)} f(\theta,\varphi)\, dl
$$

Inverse Radon–bifurcation filter (RBLE sky signature):

$$
\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
= \int_0^{2\pi}
\left[
\mathbf{M}(\alpha)\cdot
\mathcal{R}_{S^2}\!\left[\frac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}\right]
(\hat{\mathbf{n}}, \alpha)
\right] d\alpha
$$

### Term definitions

| Symbol | Definition |
|--------|------------|
| $f$ | CMB temperature or polarization field on $S^2$ |
| $\hat{\mathbf{n}}$ | Unit vector normal to great circle (sky direction) |
| $\eta$ | Arc-length offset along geodesic |
| $\mathbf{W}_{\text{string}}$ | Landscape filter from local $\Lambda(W,K)$ |
| $\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$ | RBLE signature score along axis $\hat{\mathbf{n}}$ |

### Physical meaning

If our universe nucleated from a parent Radon data stream, the injection point leaves an **anisotropic** scar — not a generic circular bubble-collision disc. The scar couples temperature and polarization through $\mathbf{M}(\alpha)$, producing a preferred axis $\hat{\mathbf{n}}_0$ locked to the stream orientation at nucleation.

### Code connection

- **`src/polomni/core/radon/transform_s2.py`** — `radon_transform_s2(healpix_map, n_hat, eta)`; healpy primary, numpy geodesic fallback.
- **`src/polomni/observatory/filters/radon_bifurcation.py`** — `inverse_radon_bifurcation_filter(map, angles)`.
- **`src/polomni/observatory/filters/string_filter.py`** — `string_landscape_filter(map, W_params)` applies $\mathbf{W}_{\text{string}}$.
- **`src/polomni/observatory/scoring/rble_signature.py`** — `compute_rble_signature(map, n_hat)` peaks $\mathcal{S}_{\text{RBLE}}$.

---

## 7. ER=EPR Bridge Conductance Tensor

### Statement

Graded entanglement–geometry coupling between districts $i$ and $j$:

$$
\mathcal{G}_{ij}(t)
= e^{-S_{\text{Euclidean}}[\text{bridge}_{ij}]/\hbar}
\cdot
\left\langle \Phi_{\text{stream}}^{(i)} \middle| \hat{T}_{\mu\nu} \middle| \Phi_{\text{stream}}^{(j)} \right\rangle
$$

District network master equation on graph $\mathcal{G}_{\text{district}}$:

$$
\frac{d\mathbf{V}_i}{dt}
= \mathcal{F}(\mathbf{V}_i)
+ \sum_{j \in \mathcal{N}(i)} \mathcal{G}_{ij}\,
\left(\mathbf{V}_j - \mathbf{V}_i\right)
+ \sum_{k=1}^{N_i} \mathcal{B}_k(\mathbf{C})\,
\delta(t - t_c)\,\mathbf{V}_i^{(k)}
$$

### Term definitions

| Symbol | Definition |
|--------|------------|
| $\mathcal{G}_{ij}$ | Wormhole bridge conductance (not binary) |
| $S_{\text{Euclidean}}[\text{bridge}_{ij}]$ | Euclidean action of ER bridge geodesic |
| $\mathbf{V}_i$ | Particle spectrum vector after Radon rotation in district $i$ |
| $\mathcal{B}_k(\mathbf{C})$ | Branching operator at choice time $t_c$ |
| $\mathcal{N}(i)$ | Graph neighbors of district $i$ |

### Physical meaning

Maldacena–Susskind (ER=EPR) is made **quantitative**: entanglement between branches born of the same parent choice event implies non-zero $\mathcal{G}_{ij}$. Child districts leak attenuated echoes to parents; travelers in choice-born black holes occupy **mixed states** across sectors weighted by conductance.

### Code connection

- **`src/polomni/core/conductance/bridge_tensor.py`** — `bridge_conductance(S_euclidean, stream_i, stream_j, T_munu_coupling)`; `conductance_matrix(district_graph)`.
- **`src/polomni/core/conductance/master_equation.py`** — `district_master_step(V, F, conductance_matrix, branch_kicks, dt)`.
- **`src/polomni/core/superspace/district_graph.py`** — `get_conductance(i, j)`, `set_conductance(i, j, value)`.
- **`src/polomni/bridge/er_epr_coupling.py`** — optional UQE density-matrix mapping to $\mathcal{G}_{ij}$.

---

## 8. Kähler Stabilization as Dynamic Boundary Condition

### Statement

Total Kähler potential with informational back-reaction and stream flux boundary term:

$$
K_{\text{total}}
= -3 M_P^2 \ln(T + \bar{T})
+ \beta\,\mathrm{Tr}\!\left(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu}\right)
+ \gamma \int_{\mathcal{H}} \Phi_{\text{stream}}^\dagger \Phi_{\text{stream}}\, dA
$$

Modulus equation from $\delta K_{\text{total}} / \delta T = 0$:

$$
\frac{\dot{T}}{T}
= -\frac{\beta}{3 M_P^2}\,\frac{d}{dt}\mathrm{Tr}(I^2)
-\frac{\gamma}{3 M_P^2}\,\frac{d}{dt}\!
\int_{\mathcal{H}} |\Phi_{\text{stream}}|^2\, dA
$$

### Term definitions

| Symbol | Definition |
|--------|------------|
| $T, \bar{T}$ | Complex structure / volume modulus and conjugate |
| $\beta$ | Informational back-reaction coefficient |
| $\gamma$ | Stream flux boundary coupling |
| $\ln(T+\bar{T})$ | Standard string volume modulus term |

### Physical meaning

Without stabilization, stream injection would **destabilize** Calabi–Yau moduli and destroy child-universe physics. $K_{\text{total}}$ acts as a self-correcting spring: extra dimensions **breathe** with each stream event, then lock to stabilized flux integers — another heritability channel distinct from standard eternal inflation.

### Code connection

- **`src/polomni/core/landscape/kahler.py`** — `kahler_total(T, T_bar, I_trace, phi_stream_flux, beta, gamma)`; `modulus_stabilization_rate(...)`.
- **`src/polomni/core/landscape/superpotential.py`** — `superpotential_W(flux_integers)`, `kahler_covariant_derivative`.
- **`src/polomni/core/landscape/vacuum_energy.py`** — feeds $\Lambda(W,K)$ back into Equation 1.

---

## Global Closure Loop

The eight equations form a closed computational cycle:

```
Λ(W,K) → P(φ,t) with D_eff → N-choice → I_μν spike → R[Ψ] → Φ_stream
    → Ψ[h,φ] wavepackets → S_RBLE on S² → G_ij bridges → K_total stabilization → Λ(W,K)
```

**Conservation spine:** Equation 4 enforces that every numeric pipeline stage preserves $\oint_{\mathcal{H}} \Phi\, dA = \mathrm{Tr}(I^2)$. See `tests/integration/test_full_loop.py`.

**Variational origin:** All eight equations arise as Euler–Lagrange projections of $\mathcal{S}_{\text{RBLE}}$ — see [VARIATIONAL_PRINCIPLE.md](./VARIATIONAL_PRINCIPLE.md).

**Observability:** Three simultaneous falsifiable predictions — see [FALSIFICATION_CRITERIA.md](./FALSIFICATION_CRITERIA.md).

---

## References within this repository

| Topic | Document |
|-------|----------|
| Symbol table | [NOTATION.md](./NOTATION.md) |
| Radon pipeline detail | [RADON_VACUUM_PIPELINE.md](./RADON_VACUUM_PIPELINE.md) |
| District graph + WDW | [SUPERSPACE_BRANCHING.md](./SUPERSPACE_BRANCHING.md) |
| String landscape | [STRING_LANDSCAPE_COUPLING.md](./STRING_LANDSCAPE_COUPLING.md) |
| CMB detection math | [CMB_OBSERVATORY_MATH.md](./CMB_OBSERVATORY_MATH.md) |
| System architecture | [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md) |
