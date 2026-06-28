# RBLE Variational Principle

The eight master equations in [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md) are not independent postulates. They are **Euler–Lagrange projections** of a single constrained action functional $\mathcal{S}_{\text{RBLE}}$ defined over district manifold $\mathcal{M}$, horizon $\mathcal{H}$, and superspace $\mathfrak{S}$.

---

## Master Action

$$
\mathcal{S}_{\text{RBLE}}
= \int_{\mathcal{M}} \sqrt{-g}\,
\Bigl[
\mathcal{L}_{\text{GR}}
+ \mathcal{L}_{\text{string}}(K,W)
+ \mathcal{L}_{\text{FP}}(P,\phi)
+ \xi\,\mathcal{L}_{\text{info}}(I_{\mu\nu})
\Bigr]\, d^4x
+ \int_{\mathcal{H}} \mathcal{L}_{\text{stream}}\!\left(
\Phi_{\text{stream}},\, \mathcal{R}[\mathbf{\Psi}],\,\mathbf{M}
\right) dA
+ \int_{\mathfrak{S}} \mathcal{L}_{\text{WDW}}\!\left(
\Psi[h_{ij},\phi],\, \Phi_{\text{stream}}
\right) d\mu_{\mathfrak{S}}
$$

### Lagrangian density terms

**General relativity (Einstein–Hilbert):**

$$
\mathcal{L}_{\text{GR}} = \frac{R}{16\pi G}
$$

**String landscape:**

$$
\mathcal{L}_{\text{string}}(K,W)
= -e^{K/M_P^2}\left(K^{I\bar{J}} D_I W \,\overline{D_J W}
- \frac{3}{M_P^2}|W|^2\right)
- \sum_{\text{uplift}} V_{\text{uplift}}
$$

**Fokker–Planck inflation:**

$$
\mathcal{L}_{\text{FP}}(P,\phi)
= P \ln P + \frac{1}{2} D_{\text{eff}}(\phi,t)\,
\left(\frac{\partial \ln P}{\partial \phi}\right)^2
+ \frac{V'(\phi)}{3H(\phi)}\, P \,\frac{\partial \chi}{\partial \phi}
$$

where $\chi$ is an auxiliary field enforcing drift–diffusion structure (De Groot–Mazur formulation).

**Information stress:**

$$
\mathcal{L}_{\text{info}}(I_{\mu\nu})
= -\frac{1}{4\xi}\, I_{\mu\nu} I^{\mu\nu}
+ J^\mu_{\text{choice}} \nabla_\mu \sigma_{\text{choice}}
$$

with auxiliary scalar $\sigma_{\text{choice}}$ enforcing the continuity constraint.

**Horizon stream (Radon boundary):**

$$
\mathcal{L}_{\text{stream}}
= \frac{1}{2}\, |\Phi_{\text{stream}}|^2
- \Phi_{\text{stream}} \cdot \left(
\mathbf{M}(\theta,\phi_{\text{ang}})\, \mathcal{R}[\mathbf{\Psi}]
\otimes \mathcal{A}_{\text{vacuum}}
\right)
$$

**Superspace Wheeler–DeWitt:**

$$
\mathcal{L}_{\text{WDW}}
= \Psi^* \hat{H}_{\text{WDW}} \Psi
- \sum_k \lambda_k\,\Psi^*\, \delta(\mathbf{p}_k - \Phi_{\text{stream}}^{(k)})\, \Psi
$$

Lagrange multipliers $\lambda_k$ enforce stream injection at the singularity.

---

## Variation and Equation Recovery

### Vary w.r.t. $g_{\mu\nu}$ → Equation 1

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta g^{\mu\nu}} = 0
\quad\Longrightarrow\quad
R_{\mu\nu} - \tfrac{1}{2} R g_{\mu\nu} + \Lambda(W,K) g_{\mu\nu}
= \frac{8\pi G}{c^4}\left(T_{\mu\nu} + \xi I_{\mu\nu}^{(N)}\right)
$$

Implementation: `omnifold_core/gravity/field_equations.py::modified_field_residual`.

### Vary w.r.t. $P$ → Equations 2 and 5

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta P} = 0
\quad\Longrightarrow\quad
\frac{\partial P}{\partial t}
= \frac{\partial}{\partial\phi}\!\left[\frac{V'}{3H} P\right]
+ D_{\text{eff}}\,\frac{\partial^2 P}{\partial \phi^2}
$$

The compact form (Eq. 2) drops $H^3/(8\pi^2)$ when $\mathcal{L}_{\text{stream}}$ dominates the horizon integral. The full form (Eq. 5) retains both terms.

Implementation: `omnifold_core/inflation/fokker_planck.py`, `drift_diffusion.py`.

### Vary w.r.t. $\Psi$ → Equation 3

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta \Psi^*} = 0
\quad\Longrightarrow\quad
\hat{H}_{\text{WDW}} \Psi
= \sum_k \lambda_k\, \delta(\mathbf{p}_k - \Phi_{\text{stream}}^{(k)})\, \Psi
$$

Setting $\lambda_k = 1$ in the discrete code basis gives the generator form of Equation 3.

Implementation: `omnifold_core/superspace/wdw_generator.py::WDWGenerator`.

### Vary w.r.t. $J^\mu_{\text{choice}}$ with constraint → Equation 4

Introduce constraint $\nabla_\mu J^\mu_{\text{choice}} = \mathcal{S}_{\text{branch}}$ via multiplier $\lambda_c(x)$:

$$
\frac{\delta}{\delta J^\mu_{\text{choice}}}\left[
\mathcal{S} + \int \lambda_c\, \nabla_\mu J^\mu_{\text{choice}}\, d^4x
\right] = 0
$$

Integration over $\Omega$ with horizon Gauss law yields the closure identity linking $\mathrm{Tr}(I^2)$ and $\oint \Phi\, dA$.

Implementation: `omnifold_core/conservation.py`.

### Vary w.r.t. $\Phi_{\text{stream}}$ on $\mathcal{H}$ → Stream definition

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta \Phi_{\text{stream}}^*} = 0
\quad\Longrightarrow\quad
\Phi_{\text{stream}}
= \mathbf{M}\cdot \mathcal{R}[\mathbf{\Psi}] \otimes \mathcal{A}_{\text{vacuum}}
$$

Implementation: `omnifold_core/radon/vacuum_stream.py::RadonVacuumPipeline`.

### Vary w.r.t. $\mathcal{G}_{ij}$ on district graph → Equation 7

Treating conductance as edge variable on graph $\mathcal{G}_{\text{district}}$:

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta \mathcal{G}_{ij}} = 0
\quad\Longrightarrow\quad
\frac{d\mathbf{V}_i}{dt} = \mathcal{F}(\mathbf{V}_i)
+ \sum_j \mathcal{G}_{ij}(\mathbf{V}_j - \mathbf{V}_i) + \text{branch kicks}
$$

Implementation: `omnifold_core/conductance/master_equation.py`.

### Vary w.r.t. $T$ (modulus) → Equation 8

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta T} = 0
\quad\Longrightarrow\quad
\frac{\dot{T}}{T} = -\frac{\beta}{3M_P^2}\frac{d}{dt}\mathrm{Tr}(I^2)
-\frac{\gamma}{3M_P^2}\frac{d}{dt}\!\int_{\mathcal{H}}|\Phi_{\text{stream}}|^2 dA
$$

Implementation: `omnifold_core/landscape/kahler.py::modulus_stabilization_rate`.

### Boundary variation on $S^2$ → Equation 6

Restricting $\mathcal{L}_{\text{stream}}$ to the CMB sky boundary $\partial\mathcal{M} \cong S^2$ and varying w.r.t. $f(\hat{\mathbf{n}})$:

$$
\frac{\delta \mathcal{S}_{\text{RBLE}}}{\delta f(\hat{\mathbf{n}})} = 0
\quad\Longrightarrow\quad
\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}}) = \int_0^{2\pi}
\mathbf{M}(\alpha)\cdot \mathcal{R}_{S^2}\!\left[\tfrac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}\right] d\alpha
$$

Implementation: `omnifold_core/radon/transform_s2.py`, `omnifold_observatory/scoring/rble_signature.py`.

---

## Conservation Constraints

The action is augmented by **hard constraints** enforced numerically and in CI:

### 1. Stream–entropy closure

$$
\oint_{\mathcal{H}} \Phi_{\text{stream}} \cdot dA
= \mathrm{Tr}\!\left(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu}\right)
\qquad \text{(Eq. 4 integrated)}
$$

Enforced by: `omnifold_core/conservation.py::enforce_stream_entropy_closure`.

### 2. Branch probability normalization

$$
\sum_{k=1}^{N} p_k = 1, \quad p_k \geq 0
$$

Enforced by: `omnifold_core/superspace/branch_operator.py::compute_branch_weights` (softmax).

### 3. District graph acyclicity

The district multiverse is a **DAG**: edges flow parent → child through black-hole portals. No closed timelike district loops.

Enforced by: `omnifold_core/superspace/district_graph.py` (NetworkX `DiGraph` + `is_directed_acyclic_graph` check).

### 4. Energy–momentum consistency (weak field)

In the district weak-field limit, the modified Einstein residual must satisfy:

$$
\|\nabla_\mu T^{\mu\nu}_{\text{total}}\| < \epsilon_{\text{numerical}}
$$

where $T^{\mu\nu}_{\text{total}} = T^{\mu\nu} + \xi I^{\mu\nu}$.

Enforced by: `omnifold_core/gravity/field_equations.py` tests.

### 5. Moduli stability bound

After stream injection, volume modulus must satisfy:

$$
\left|\frac{\Delta T}{T}\right| < \Delta T_{\max}
\quad\text{(stabilization succeeds)}
$$

Enforced by: `omnifold_core/landscape/kahler.py` and integration tests.

---

## Discrete Action (Code Correspondence)

The continuous action maps to the simulation loop as follows:

| Continuous object | Discrete implementation |
|-------------------|-------------------------|
| $\int_{\mathcal{M}} \sqrt{-g}\,\mathcal{L}\, d^4x$ | Grid-based field evaluation on district voxels |
| $\int_{\mathcal{H}} \mathcal{L}_{\text{stream}}\, dA$ | `stream_flux_integral(phi_stream, horizon_area)` |
| $\int_{\mathfrak{S}} \mathcal{L}_{\text{WDW}}$ | `WDWGenerator.spawn_wavepackets` |
| $\mathcal{R}[\mathbf{\Psi}]$ | `radon_transform_r3` / `radon_transform_s2` |
| $\mathcal{G}_{ij}$ | Edge attributes on `DistrictGraph` |

---

## Relation to Effective Field Theory

Even if full string compactification is truncated in code, $\mathcal{S}_{\text{RBLE}}$ remains well-defined as an **effective action** when:

1. $\Lambda(W,K)$ is parameterized by flux integers (not full CY geometry).
2. $\hat{H}_{\text{WDW}}$ is replaced by a mini-superspace (Friedmann–Robertson–Walker) reduction.
3. $\mathcal{R}_{S^2}$ operates on HEALPix pixel rings.

The variational structure guarantees that **consistent perturbations** (e.g., changing $\xi$ or $\lambda$) propagate coherently through gravity, inflation, stream, and sky modules — not as ad hoc coupling constants per script.

---

## Further reading

- [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md) — full equation statements
- [NOTATION.md](./NOTATION.md) — symbol reference
- [FALSIFICATION_CRITERIA.md](./FALSIFICATION_CRITERIA.md) — observational consequences of $\mathcal{S}_{\text{RBLE}}$
