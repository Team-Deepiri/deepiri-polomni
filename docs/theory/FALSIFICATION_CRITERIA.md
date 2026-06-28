# RBLE Falsification Criteria

RBLE is designed **falsification-first**: the framework makes simultaneous predictions that standard eternal inflation, isolated bubble-collision models, and pure string landscape statistics do **not** make together. This document defines null hypotheses, test statistics, and what survives if each test fails.

**Implementation:** `src/polomni/observatory/scoring/rble_signature.py` returns `DetectionReport` with `falsification_flags`. See [CMB_OBSERVATORY_MATH.md](./CMB_OBSERVATORY_MATH.md) for detection statistics.

---

## Overview: Three Simultaneous Predictions

For RBLE to be supported at research grade, **all three** must hold above established significance thresholds in independent datasets:

| ID | Prediction | Primary observable | Module |
|----|------------|-------------------|--------|
| **P1** | Radon-anisotropic CMB scars with $T$–$E$ coupling | Planck / Simons / LiteBIRD maps | `polomni.observatory` |
| **P2** | Spatially clustered non-Gaussianity along district graph | $f_{\mathrm{NL}}$ proxies, directed $D_{\text{eff}}$ | `src/polomni/core/inflation` |
| **P3** | Correlated GW ringdown phases across parent-linked events | LIGO/Virgo/KAGRA catalog | `src/polomni/core/conductance` (stub adapter) |

Failure of all three does **not** invalidate every RBLE layer — see [What Survives Falsification](#what-survives-falsification).

---

## Prediction P1: Radon-Anisotropic CMB Scars

### RBLE claim

CMB "bruises" from parent-universe stream injection are **not** generic circular temperature discs. They exhibit:

1. **Anisotropic ring geometry** from geodesic Radon projection on $S^2$
2. **Spin-aligned polarization** via $\mathbf{M}(\alpha)$ rotation
3. **Preferred axis** $\hat{\mathbf{n}}_0$ locked to stream orientation at nucleation
4. **String-filtered harmonic ladder** from $\mathbf{W}_{\text{string}}(\Lambda(W,K))$

Signature functional:

$$
\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
= \int_0^{2\pi}
\mathbf{M}(\alpha)\cdot
\mathcal{R}_{S^2}\!\left[\frac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}\right]
(\hat{\mathbf{n}}, \alpha)\, d\alpha
$$

### Null hypothesis $H_0^{(1)}$

**Standard bubble collision / isotropic anomaly null:**

CMB temperature fluctuations on large angular scales are consistent with:

- Isotropic Gaussian random field (GRF) with Planck best-fit $\Lambda$CDM power spectrum $C_\ell^{TT}$
- Any localized anomalies follow **circularly symmetric** profiles (Azimuthally averaged disc correlation)
- No statistically significant $T$–$E$ mode coupling beyond $\Lambda$CDM expectations
- $\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$ is **flat** across all $\hat{\mathbf{n}}$ (no preferred axis)

Formally, for rotation-averaged scar statistic $S_{\max} = \max_{\hat{\mathbf{n}}} \mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$:

$$
H_0^{(1)}: \quad S_{\max} \sim \mathcal{F}_{\text{null}}(C_\ell^{TT})
$$

where $\mathcal{F}_{\text{null}}$ is the distribution from `src/polomni/observatory/scoring/null_ensemble.py::generate_null_ensemble`.

### Alternative hypothesis $H_A^{(1)}$

$$
H_A^{(1)}: \quad S_{\max} > S_{\text{threshold}}
\quad\text{and}\quad
\rho_{TE}(\hat{\mathbf{n}}_0) > \rho_{TE}^{\text{null}} + 3\sigma
$$

where $\rho_{TE}$ is the $T$–$E$ cross-correlation along axis $\hat{\mathbf{n}}_0$.

### Test procedure

1. Load HEALPix map via `src/polomni/observatory/ingest/healpix_loader.py`
2. Extract $Q,U$ via `polarization.py::extract_qu_maps`
3. Apply `filters/radon_bifurcation.py` and `filters/string_filter.py`
4. Compute $\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$ on HEALPix pixel ring directions
5. Compare $S_{\max}$ to null ensemble ($N \geq 10^4$ maps)
6. Report $p$-value and `falsification_flags.p1_radon_scar`

### Falsification threshold

Reject RBLE sky layer if, after multiple-comparison correction (Bonferroni over $\sim 10^5$ independent axes at NSIDE=2048):

$$
p < 0.01 \quad\text{and}\quad \text{injection recovery test fails}
$$

Injection recovery: synthetic Radon scar at known $\hat{\mathbf{n}}_{\text{inj}}$ must be recovered with axis error $< 5°$ at SNR $\geq 3$ (`tests/observatory/test_rble_signature.py`).

---

## Prediction P2: Clustered Directed Non-Gaussianity

### RBLE claim

Radon-modified diffusion (Equations 2 and 5) produces **spatially clustered** non-Gaussianity:

$$
D_{\text{eff}}(\phi,t)
= \frac{H^3}{8\pi^2}
+ \lambda \sum_k w_k \iint_{\mathcal{H}_k}
\left\|\mathbf{M}_k \cdot \mathcal{R}_k[\mathbf{\Psi}]\right\|_{\mathbf{g}_k}^2 dA
$$

Unlike homogeneous eternal inflation, $f_{\mathrm{NL}}$ proxies correlate with **district graph geodesics** — patches closer on the reconstructed DAG share directed diffusion history.

### Null hypothesis $H_0^{(2)}$

**Homogeneous inflation null:**

- $D_{\text{eff}} = H^3/(8\pi^2)$ only (no stream term)
- $f_{\mathrm{NL}}^{\text{local}}$ is **spatially uncorrelated** beyond standard cosmic variance
- Directed diffusion estimator $\hat{D}_{\text{directed}}(\mathbf{x})$ has zero mean across sky patches

$$
H_0^{(2)}: \quad \mathrm{Cov}\!\left(\hat{f}_{\mathrm{NL}}(\mathbf{x}_i),\,
\hat{f}_{\mathrm{NL}}(\mathbf{x}_j)\right)
= \delta_{ij}\, \sigma_{\mathrm{CV}}^2
$$

### Alternative hypothesis $H_A^{(2)}$

$$
H_A^{(2)}: \quad C_{ij}^{\text{district}}
= \exp\!\left(-d_{\mathcal{G}}(i,j)/\ell_0\right) > 0
$$

where $d_{\mathcal{G}}$ is graph distance on reconstructed district DAG and $\ell_0 > 0$ is a correlation length.

### Test procedure

1. Run `polomni simulate` to produce district DAG + stream history
2. Map districts to sky patches via stream axis $\hat{\mathbf{n}}_0^{(k)}$
3. Estimate local $f_{\mathrm{NL}}$ proxy via bispectrum estimator or `directed_diffusion` residual
4. Compute Moran's $I$ spatial autocorrelation vs. district graph distance
5. Compare to shuffled-graph null (preserve marginals, randomize edges)

### Falsification threshold

Reject RBLE inflation layer if Moran's $I$ satisfies $|I| < 0.05$ with $p > 0.05$ on both simulated and observational proxies, **and** directed diffusion term $\lambda \langle \Phi^2 \rangle / (H^3/8\pi^2) < 10^{-3}$ everywhere.

---

## Prediction P3: GW Ringdown Phase Correlations

### RBLE claim

ER=EPR conductance $\mathcal{G}_{ij}$ predicts **sub-percent phase correlations** between gravitational-wave ringdown modes from black-hole merger events that share a parent choice node on the district graph:

$$
\mathcal{G}_{ij}(t)
= e^{-S_{\text{Euclidean}}[\text{bridge}_{ij}]/\hbar}
\left\langle \Phi_{\text{stream}}^{(i)} \middle| \hat{T}_{\mu\nu} \middle| \Phi_{\text{stream}}^{(j)} \right\rangle
$$

Standard GR: ringdown phases of spatially separated events are **uncorrelated**.

### Null hypothesis $H_0^{(3)}$

For ringdown phase vectors $\boldsymbol{\phi}_a, \boldsymbol{\phi}_b$ from events $a, b$:

$$
H_0^{(3)}: \quad
\rho_{\phi}(a,b) = \frac{\boldsymbol{\phi}_a \cdot \boldsymbol{\phi}_b}
{|\boldsymbol{\phi}_a||\boldsymbol{\phi}_b|} \sim \mathcal{N}(0, \sigma_{\text{noise}}^2)
\quad \forall\, a \neq b
$$

### Alternative hypothesis $H_A^{(3)}$

For events linked by parent choice node $c$ on district graph:

$$
H_A^{(3)}: \quad
\rho_{\phi}(a,b) = \mathcal{G}_{ab} \cdot \rho_0,
\quad \mathcal{G}_{ab} > 0
\quad \text{if } \exists\, c: \; a,b \in \text{descendants}(c)
$$

### Test procedure (future catalog adapter)

1. Ingest ringdown phase catalog (LIGO/Virgo/KAGRA)
2. Reconstruct district graph from simulation or astrophysical priors
3. Compute `conductance_matrix(district_graph)`
4. Stratify event pairs: linked vs. unlinked
5. Two-sample test on $\rho_\phi$ distributions

**Current status:** stub in `src/polomni/core/conductance/`; falsification flag defaults to `inconclusive` until catalog adapter ships.

### Falsification threshold

Reject RBLE bridge layer if:

$$
|\langle \rho_\phi \rangle_{\text{linked}} - \langle \rho_\phi \rangle_{\text{unlinked}}| < 0.001
\quad\text{with}\quad p > 0.1
$$

after $\geq 50$ linked pairs (projected O4/O5 catalog depth).

---

## Combined Falsification Matrix

| Outcome | P1 (CMB) | P2 ($f_{\mathrm{NL}}$) | P3 (GW) | Interpretation |
|---------|----------|------------------------|---------|----------------|
| **Full support** | Pass | Pass | Pass | RBLE loop validated |
| **Sky only** | Pass | Fail | Fail | Radon scar real; inflation/bridge effective theory only |
| **Inflation only** | Fail | Pass | Fail | Directed diffusion useful; sky layer wrong |
| **Bridge only** | Fail | Fail | Pass | ER=EPR conductance survives; rest effective |
| **Full rejection** | Fail | Fail | Fail | See survival table below |

---

## What Survives Falsification

RBLE is layered. Each layer can survive as **effective field theory** even if higher layers fail:

| Layer | Survives if… | Remaining utility |
|-------|--------------|-------------------|
| **Information stress $I_{\mu\nu}$** | Always (mathematical) | Modified gravity simulations, PINN metric solver |
| **Radon vacuum pipeline** | P1 fails but conservation holds | Holographic district compression, data engineering |
| **Directed Fokker–Planck** | P2 fails partially | Inflation emulator with parent-biased noise |
| **District DAG + branching** | P1, P2 fail | Graph-NODE multiverse simulator, game-theoretic cosmology |
| **WDW generator** | Observational failure | Mini-superspace spawning toy model |
| **ER=EPR conductance** | P3 fails | UQE bridge still valid for quantum sims |
| **Kähler stabilization** | String layer truncated | Moduli breathing for stream shocks |

Document in `DetectionReport.falsification_flags` which layers remain **active**, **deprecated**, or **effective-only**.

---

## Code-Enforced Invariants (Non-Falsifiable Internally)

These must hold in **every** simulation regardless of observational outcome:

1. $\sum_k p_k = 1$ (branch weights)
2. $\oint_{\mathcal{H}} \Phi\, dA = \mathrm{Tr}(I^2)$ (conservation)
3. District graph is acyclic
4. $D_{\text{eff}} \geq 0$ everywhere

Violations indicate **implementation bugs**, not physics falsification. See `src/polomni/core/conservation.py` and `tests/integration/test_full_loop.py`.

---

## Reporting Standard

`src/polomni/observatory/reports/detection_report.py::format_report` must include:

```json
{
  "rble_score": 0.0,
  "preferred_axis": [0.0, 0.0, 1.0],
  "p_value_null": 1.0,
  "falsification_flags": {
    "p1_radon_scar": "pass|fail|inconclusive",
    "p2_clustered_fnl": "pass|fail|inconclusive",
    "p3_gw_ringdown": "pass|fail|inconclusive",
    "surviving_layers": ["conservation", "radon_pipeline"]
  }
}
```

---

## Related documents

- [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md) — Equations 2, 5, 6, 7
- [CMB_OBSERVATORY_MATH.md](./CMB_OBSERVATORY_MATH.md) — P1 detection statistics in detail
- [VARIATIONAL_PRINCIPLE.md](./VARIATIONAL_PRINCIPLE.md) — constraint structure
