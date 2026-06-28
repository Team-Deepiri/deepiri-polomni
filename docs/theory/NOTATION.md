# RBLE Notation Reference

Complete symbol table for the **Radon-Bifurcated Landscape Engine (RBLE)** as implemented in `deepiri-omnifold`. Greek indices $\mu,\nu = 0,1,2,3$ (spacetime); $i,j,k$ district/branch indices; $I,\bar{J}$ Calabi–Yau moduli indices.

**Canonical equations:** [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md)

---

## Spacetime and Geometry

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $g_{\mu\nu}$ | Tensor | Spacetime metric | `gravity/field_equations.py` |
| $R_{\mu\nu}$ | Tensor | Ricci tensor | `gravity/field_equations.py` |
| $R$ | Scalar | Ricci scalar curvature | `gravity/field_equations.py` |
| $G_{\mu\nu}$ | Tensor | Einstein tensor $R_{\mu\nu} - \frac{1}{2} R g_{\mu\nu}$ | `gravity/field_equations.py` |
| $T_{\mu\nu}$ | Tensor | Stress-energy tensor | `gravity/field_equations.py` |
| $h_{ij}$ | Tensor | Spatial 3-metric on Cauchy slice | `superspace/wdw_generator.py` |
| $R^{(3)}$ | Scalar | Intrinsic 3-curvature | `superspace/wdw_generator.py` |
| $G_{ijkl}$ | Tensor | DeWitt superspace metric | `superspace/wdw_generator.py` |
| $\mathcal{H}$ | Surface | Event horizon of graviton well | `radon/vacuum_stream.py` |
| $\mathcal{M}$ | Manifold | District spacetime region | `superspace/district_graph.py` |
| $\mathfrak{S}$ | Manifold | Superspace of 3-geometries | `superspace/wdw_generator.py` |
| $S^2$ | Manifold | CMB celestial sphere | `radon/transform_s2.py` |
| $\mathbf{g}_k$ | Matrix | Branch-$k$ metric (finite-dim) | `superspace/branch_operator.py` |
| $ds^2$ | Scalar | Line element | `gravity/schwarzschild_choice.py` |

---

## Unified State and Fields

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $\mathbf{\Psi}(t)$ | Vector | Unified state $[X, P, \Lambda, C]^T$ | `state/unified_state.py::UnifiedStateVector` |
| $\mathbf{X}_{\text{spatial}}$ | Vector | Spatial coordinates | `state/unified_state.py` |
| $\mathbf{P}_{\text{momentum}}$ | Vector | Momentum sector | `state/unified_state.py` |
| $\mathbf{\Lambda}_{\text{laws}}$ | Vector | Local physical constants | `state/unified_state.py` |
| $\mathbf{C}_{\text{choice}}$ | Vector | Multi-choice encoding | `state/unified_state.py` |
| $\phi$ | Scalar | Inflaton field | `inflation/fokker_planck.py` |
| $P(\phi,t)$ | Scalar | Inflation field-space PDF | `inflation/fokker_planck.py` |
| $V(\phi)$ | Scalar | Inflaton potential | `inflation/drift_diffusion.py` |
| $H(\phi)$ | Scalar | Hubble parameter | `inflation/drift_diffusion.py` |
| $\Psi[h_{ij},\phi]$ | Functional | Wave function of the universe | `superspace/wdw_generator.py` |
| $\hat{H}_{\text{WDW}}$ | Operator | Wheeler–DeWitt Hamiltonian | `superspace/wdw_generator.py` |
| $\hat{H}_{\text{matter}}$ | Operator | Matter Hamiltonian in superspace | `superspace/wdw_generator.py` |

---

## Information, Choice, and Conservation

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $I_{\mu\nu}^{(N)}$ | Tensor | $N$-choice informational stress | `gravity/information_tensor.py` |
| $I_{\text{choice}}$ | Scalar | Choice entropy magnitude | `gravity/schwarzschild_choice.py` |
| $\xi$ | Scalar | Info–gravity coupling | `gravity/field_equations.py` |
| $\gamma$ | Scalar | Schwarzschild choice coupling | `gravity/schwarzschild_choice.py` |
| $J^\mu_{\text{choice}}$ | Vector | Information current | `conservation.py` |
| $p_k$ | Scalar | Branch probability weight | `superspace/branch_operator.py` |
| $p_0$ | Scalar | Reference branch probability | `superspace/branch_operator.py` |
| $N$ | Integer | Number of choice branches | `superspace/district_graph.py` |
| $\mathcal{B}_k$ | Operator | Branch spawning operator | `superspace/branch_operator.py` |
| $t_c$ | Scalar | Choice event time | `superspace/particle_langevin.py` |
| $\delta(t-t_c)$ | Distribution | Temporal kick at choice | `superspace/particle_langevin.py` |
| $\delta^{(4)}(x-x_k)$ | Distribution | Spacetime branch source | `conservation.py` |
| $\mathrm{Tr}(I^2)$ | Scalar | $\mathrm{Tr}(I_{\mu\nu} I^{\mu\nu})$ | `gravity/information_tensor.py` |

---

## String Landscape

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $W$ | Scalar | Superpotential | `landscape/superpotential.py` |
| $K$ | Scalar | Kähler potential | `landscape/kahler.py` |
| $K_{\text{total}}$ | Scalar | Stabilized total Kähler potential | `landscape/kahler.py` |
| $T, \bar{T}$ | Scalar | Volume modulus and conjugate | `landscape/kahler.py` |
| $D_I$ | Operator | Kähler covariant derivative | `landscape/superpotential.py` |
| $\Lambda(W,K)$ | Scalar | Landscape vacuum energy / CC | `landscape/vacuum_energy.py` |
| $\langle V_D \rangle$ | Scalar | 4D effective potential | `landscape/vacuum_energy.py` |
| $M_P$ | Scalar | Reduced Planck mass | `landscape/vacuum_energy.py` |
| $\beta$ | Scalar | Informational Kähler back-reaction | `landscape/kahler.py` |
| $\gamma_K$ | Scalar | Stream flux Kähler coupling ($\gamma$ in Eq. 8) | `landscape/kahler.py` |
| $V_{\text{uplift}}$ | Scalar | Uplift potential terms | `landscape/vacuum_energy.py` |
| $\mathbf{W}_{\text{string}}$ | Vector/Filter | String landscape CMB filter | `omnifold_observatory/filters/string_filter.py` |

---

## Radon Transform and Stream

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $\mathcal{R}[\mathbf{\Psi}]$ | Functional | Radon transform in $\mathbb{R}^3$ | `radon/transform_r3.py` |
| $\mathcal{R}_{S^2}[f]$ | Functional | Geodesic Radon on sphere | `radon/transform_s2.py` |
| $\boldsymbol{\xi}$ | Vector | Radon slice direction (unit) | `radon/transform_r3.py` |
| $p$ | Scalar | Radon plane offset | `radon/transform_r3.py` |
| $\hat{\mathbf{n}}$ | Vector | Great-circle normal on $S^2$ | `radon/transform_s2.py` |
| $\eta$ | Scalar | Geodesic arc parameter | `radon/transform_s2.py` |
| $\mathbf{M}(\theta,\phi,\psi)$ | Matrix | $SO(3)$ Euler rotation | `radon/so3_rotation.py` |
| $\mathbf{M}(\alpha)$ | Matrix | Sky-scan rotation angle | `omnifold_observatory/filters/radon_bifurcation.py` |
| $\Phi_{\text{stream}}$ | Vector | Vacuum data stream | `state/stream_packet.py`, `radon/vacuum_stream.py` |
| $\mathcal{A}_{\text{vacuum}}$ | Vector | Graviton vacuum vector potential | `radon/vacuum_stream.py` |
| $\mathbf{V}_p$ | Vector | Particle spectrum vector | `radon/so3_rotation.py::extract_particle_spectrum` |
| $\mathbf{V}_i$ | Vector | District-$i$ spectrum vector | `conductance/master_equation.py` |
| $\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$ | Scalar | RBLE CMB signature score | `omnifold_observatory/scoring/rble_signature.py` |
| $\Delta T / T$ | Field | CMB temperature fluctuation | `omnifold_observatory/ingest/healpix_loader.py` |
| $Q, U$ | Fields | Stokes polarization parameters | `omnifold_observatory/ingest/polarization.py` |

---

## Inflation and Diffusion

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $D_{\text{eff}}$ | Scalar | Effective diffusion coefficient | `inflation/fokker_planck.py` |
| $\lambda$ | Scalar | Stream–diffusion coupling | `inflation/fokker_planck.py` |
| $w_k$ | Scalar | District weight in diffusion sum | `inflation/fokker_planck.py` |
| $f_{\mathrm{NL}}$ | Scalar | Local non-Gaussianity parameter | `inflation/drift_diffusion.py` (proxy) |
| $V'(\phi)$ | Scalar | $\partial V / \partial \phi$ | `inflation/drift_diffusion.py` |

---

## District Graph and Conductance

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $\mathcal{G}_{\text{district}}$ | Graph | Directed acyclic district graph | `superspace/district_graph.py` |
| $\mathcal{G}_{ij}$ | Scalar | ER=EPR bridge conductance | `conductance/bridge_tensor.py` |
| $\mathcal{N}(i)$ | Set | Graph neighbors of district $i$ | `superspace/district_graph.py` |
| $S_{\text{Euclidean}}[\text{bridge}]$ | Scalar | Euclidean wormhole action | `conductance/bridge_tensor.py` |
| $\mathcal{F}(\mathbf{V})$ | Vector fn | Local district dynamics | `conductance/master_equation.py` |
| $\mathbf{p}_k$ | Vector | Superspace momentum branch $k$ | `superspace/particle_langevin.py` |
| $\mathcal{V}_{\text{graviton}}$ | Scalar | Graviton well potential | `superspace/particle_langevin.py` |
| $\sigma$ | Scalar | Langevin noise amplitude | `superspace/particle_langevin.py` |
| $d\mathbf{W}_t$ | Process | Wiener increment | `superspace/particle_langevin.py` |

---

## Fundamental Constants and Units

| Symbol | Value (SI) | Notes |
|--------|------------|-------|
| $G$ | $6.674 \times 10^{-11}\,\mathrm{m^3 kg^{-1} s^{-2}}$ | Newton constant |
| $c$ | $2.998 \times 10^8\,\mathrm{m/s}$ | Speed of light |
| $\hbar$ | $1.055 \times 10^{-34}\,\mathrm{J\,s}$ | Reduced Planck constant |
| $k_B$ | $1.381 \times 10^{-23}\,\mathrm{J/K}$ | Boltzmann (CMB units) |

**Code convention:** Natural units ($c = \hbar = M_P = 1$) unless docstring or test specifies SI. CLI and observatory use dimensionless HEALPix amplitudes in $\mu K$.

---

## Action and Variational

| Symbol | Type | Definition | Code / module |
|--------|------|------------|---------------|
| $\mathcal{S}_{\text{RBLE}}$ | Functional | Master RBLE action | `docs/theory/VARIATIONAL_PRINCIPLE.md` |
| $\mathcal{L}_{\text{GR}}$ | Density | Einstein–Hilbert Lagrangian | `gravity/field_equations.py` |
| $\mathcal{L}_{\text{string}}$ | Density | Landscape Lagrangian | `landscape/vacuum_energy.py` |
| $\mathcal{L}_{\text{FP}}$ | Density | Fokker–Planck Lagrangian | `inflation/fokker_planck.py` |
| $\mathcal{L}_{\text{info}}$ | Density | Information stress Lagrangian | `gravity/information_tensor.py` |
| $\mathcal{L}_{\text{stream}}$ | Density | Horizon stream boundary Lagrangian | `radon/vacuum_stream.py` |
| $\mathcal{L}_{\text{WDW}}$ | Density | Superspace generator Lagrangian | `superspace/wdw_generator.py` |

---

## Pydantic / Code Types

| Code name | Maps to | Module |
|-----------|---------|--------|
| `UnifiedStateVector` | $\mathbf{\Psi}(t)$ | `state/unified_state.py` |
| `StreamPacket` | $\Phi_{\text{stream}}$ + metadata | `state/stream_packet.py` |
| `ChoiceEvent` | $(t_c, N, \text{parent\_id})$ | `state/choice_event.py` |
| `Wavepacket` | Superspace branch packet | `superspace/wdw_generator.py` |
| `DetectionReport` | $\mathcal{S}_{\text{RBLE}}$, axis, flags | `omnifold_observatory/scoring/rble_signature.py` |
| `DistrictGraph` | $\mathcal{G}_{\text{district}}$ | `superspace/district_graph.py` |

---

## Index and Abbreviation Conventions

| Convention | Meaning |
|------------|---------|
| $(\mu,\nu,\rho,\sigma)$ | Spacetime tensor indices, 0–3 |
| $(i,j,k,\ell)$ | Spatial / district / branch indices |
| $(I,\bar{J})$ | Kähler moduli indices |
| $\hat{\mathbf{n}}$ | Unit vector on $S^2$ (hat = sky direction) |
| Overbar ($\bar{T}$, $\overline{D_J W}$) | Complex conjugate |
| Superscript $(N)$ | Dependence on $N$-way choice |
| Subscript $k$ | Branch or district label |
| RBLE | Radon-Bifurcated Landscape Engine |
| ER=EPR | Einstein–Rosen = Einstein–Podolsky–Rosen |
| WDW | Wheeler–DeWitt |
| HEALPix | Hierarchical Equal Area isoLatitude Pixelization |
| CC | Cosmological constant |
| DAG | Directed acyclic graph |
| PINN | Physics-informed neural network |
| GRF | Gaussian random field |

---

## Quick cross-reference

$$
\underbrace{\Lambda(W,K)}_{\text{landscape}}
\;\longrightarrow\;
\underbrace{P(\phi,t;\, D_{\text{eff}})}_{\text{inflation}}
\;\longrightarrow\;
\underbrace{I_{\mu\nu}^{(N)}}_{\text{gravity}}
\;\longrightarrow\;
\underbrace{\mathcal{R}[\mathbf{\Psi}] \to \Phi_{\text{stream}}}_{\text{radon}}
\;\longrightarrow\;
\underbrace{\Psi[h,\phi]}_{\text{superspace}}
\;\longrightarrow\;
\underbrace{\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})}_{\text{observatory}}
\;\longleftrightarrow\;
\underbrace{\mathcal{G}_{ij}}_{\text{conductance}}
\;\longrightarrow\;
\underbrace{K_{\text{total}}}_{\text{landscape}}
$$
