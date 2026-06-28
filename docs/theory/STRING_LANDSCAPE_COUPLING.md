# String Landscape Coupling

How the **string landscape** ($W$, $K$, $\Lambda$) couples to RBLE district physics, moduli stabilization, and the modified Einstein equations.

**Master equations:** Equations 1 and 8 in [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md). **Implementation:** `src/polomni/core/landscape/`.

---

## Role in RBLE Loop

The string landscape supplies the **background vacuum energy** that competes with choice-induced informational stress:

$$
\underbrace{\Lambda(W,K)\, g_{\mu\nu}}_{\text{landscape stabilizer}}
\;\longleftrightarrow\;
\underbrace{\xi\, I_{\mu\nu}^{(N)}}_{\text{choice destabilizer}}
$$

When $\xi \,\mathrm{Tr}(I^2) > |\Lambda(W,K)|$ locally, the district metric collapses → graviton well → Radon stream → new superspace wavepacket with **mutated flux integers**.

---

## Superpotential $W$

### Flux compactification

In type IIB / M-theory compactifications on Calabi–Yau threefolds:

$$
W = \int_{\text{CY}} G_3 \wedge \Omega
$$

Discrete flux integers $\{n_I\}$ on cycles of CY determine $W$ up to continuous moduli.

### Discrete code model

For flux vector $\mathbf{n} = (n_1, \ldots, n_F)$:

$$
W(\mathbf{n}) = W_0 + \sum_I c_I n_I + \sum_{I<J} d_{IJ} n_I n_J
$$

**Code:** `landscape/superpotential.py::superpotential_W(flux_integers: list[int])`

Symbolic mode uses SymPy; numeric mode evaluates for simulation.

### Kähler covariant derivative

$$
D_I W = \partial_I W + \frac{1}{M_P^2} W\, \partial_I K
$$

**Code:** `landscape/superpotential.py::kahler_covariant_derivative(W, K, moduli_index)`

---

## Kähler Potential $K$

### Standard volume modulus term

$$
K_0 = -3 M_P^2 \ln(T + \bar{T})
$$

where $T$ controls the size of extra dimensions.

### RBLE stabilization extension (Equation 8)

$$
K_{\text{total}}
= -3 M_P^2 \ln(T + \bar{T})
+ \beta\, \mathrm{Tr}\!\left(I_{\mu\nu}^{(N)} I^{(N)\,\mu\nu}\right)
+ \gamma \int_{\mathcal{H}} \Phi_{\text{stream}}^\dagger \Phi_{\text{stream}}\, dA
$$

| Term | Physical role |
|------|---------------|
| $\ln(T+\bar{T})$ | Volume modulus tracking |
| $\beta\,\mathrm{Tr}(I^2)$ | Absorb choice entropy shock |
| $\gamma \int_{\mathcal{H}}|\Phi|^2 dA$ | Stream flux boundary damping |

**Code:** `landscape/kahler.py::kahler_total(T, T_bar, I_trace, phi_stream_flux, beta, gamma)`

### Modulus stabilization rate

From $\delta K_{\text{total}} / \delta T = 0$:

$$
\frac{\dot{T}}{T}
= -\frac{\beta}{3 M_P^2}\,\frac{d}{dt}\mathrm{Tr}(I^2)
-\frac{\gamma}{3 M_P^2}\,\frac{d}{dt}\!
\int_{\mathcal{H}} |\Phi_{\text{stream}}|^2\, dA
$$

**Code:** `landscape/kahler.py::modulus_stabilization_rate(...)`

### Stability criterion

Child universe survives if after stream injection:

$$
\left|\frac{\Delta T}{T}\right| < \Delta T_{\max}
\quad\text{and}\quad
\frac{d^2 V_{\text{eff}}}{dT^2}\bigg|_{T_*} > 0
$$

---

## Cosmological Constant $\Lambda(W,K)$

### Landscape formula

$$
\Lambda(W,K) = \langle V_D \rangle
= e^{K/M_P^2}\left(
K^{I\bar{J}} D_I W \,\overline{D_J W}
- \frac{3}{M_P^2}|W|^2
\right)
+ \sum_{\text{uplift}} V_{\text{uplift}}
$$

This is the **F-term potential** of $N=1$ supergravity in 4D effective theory.

**Code:** `landscape/vacuum_energy.py::lambda_vacuum(W, K, M_P=1.0)`

### Competition with information stress

Modified Einstein equation (Equation 1):

$$
G_{\mu\nu} + \Lambda(W,K)\, g_{\mu\nu}
= \frac{8\pi G}{c^4}\left(T_{\mu\nu} + \xi I_{\mu\nu}^{(N)}\right)
$$

Define **collapse criterion** at district scale:

$$
\mathcal{C}_{\text{collapse}}
= \frac{\xi\, \mathrm{Tr}(I^2)}{|\Lambda(W,K)| + \epsilon}
> 1
\quad\Longrightarrow\quad \text{graviton well forms}
$$

---

## Moduli Stabilization Dynamics

### Effective potential

$$
V_{\text{eff}}(T) = e^{K/M_P^2}\left(
K^{I\bar{J}} D_I W \,\overline{D_J W}
- \frac{3}{M_P^2}|W|^2
\right)\bigg|_{T}
$$

Stream events perturb $V_{\text{eff}}$ through $K_{\text{total}}$:

$$
\Delta V_{\text{eff}} \approx
\frac{\partial V_{\text{eff}}}{\partial K}\,
\Delta K_{\text{total}}
$$

where $\Delta K_{\text{total}} = \beta\,\Delta\mathrm{Tr}(I^2) + \gamma \Delta\|\Phi\|^2$.

### Heritability channel

Unlike memoryless eternal inflation, RBLE child districts inherit:

1. **Flux integers** — discretized from parent $W$ plus stream-induced shift
2. **Stabilized modulus** $T_*$ — from post-stream Kähler relaxation
3. **Local $\Lambda$** — recomputed at child node in `DistrictGraph`

```python
# district_graph.py node attribute
lambda_vacuum = lambda_vacuum(W_child, K_total_child)
```

---

## Coupling to Inflation ($D_{\text{eff}}$)

Landscape sets $H(\phi)$ and baseline diffusion $H^3/(8\pi^2)$. Stream-modified term:

$$
D_{\text{eff}} = \frac{H^3}{8\pi^2}
+ \lambda \sum_k w_k \iint_{\mathcal{H}_k}
\left\|\mathbf{M}_k \cdot \mathcal{R}_k[\mathbf{\Psi}]\right\|^2 dA
$$

District weight $w_k \propto \exp(-|\Lambda_k| / \Lambda_*)$ — patches nearer vacuum degeneracy are more sensitive to stream bias.

**Code:** `inflation/fokker_planck.py::radon_modified_D_eff`

---

## Coupling to CMB Filter

String landscape enters sky signature as filter tensor:

$$
\mathbf{W}_{\text{string}} = \mathbf{W}(\Lambda(W,K), \{n_I\})
$$

Scars from parent universes with **different flux vacua** leave distinct harmonic ladders — not generic collision profiles.

**Code:** `src/polomni/observatory/filters/string_filter.py::string_landscape_filter(map, W_params)`

---

## Landscape Statistics (Conceptual)

Typical CY compactifications admit $\sim 10^{500}$ metastable vacua. RBLE does **not** sample uniformly:

- District choice events **navigate** the landscape via stream-induced flux jumps
- Conductance $\mathcal{G}_{ij}$ biases backward information flow
- Graph distance correlates with $\Delta \Lambda$ between sectors

Future: `src/polomni/neural/graph_node/engine.py::RBLEGraphEngine` learns landscape navigation policy.

---

## Parameter Summary

| Parameter | Typical role | Module |
|-----------|--------------|--------|
| $W_0, c_I, d_{IJ}$ | Superpotential shape | `superpotential.py` |
| $\beta$ | Info–Kähler coupling | `kahler.py` |
| $\gamma$ | Stream–Kähler coupling | `kahler.py` |
| $M_P$ | Planck scale (natural units: 1) | `vacuum_energy.py` |
| $\xi$ | Info–gravity coupling | `gravity/field_equations.py` |
| $\lambda$ | Stream–diffusion coupling | `inflation/fokker_planck.py` |
| $\epsilon$ | Numerical regularization | various |

---

## Module Dependency Graph

```
superpotential.py ──► vacuum_energy.py ──► lambda_vacuum
        │                      │
        ▼                      ▼
    kahler.py ◄── I_trace, phi_stream_flux
        │
        ├──► gravity/field_equations.py (Λ on LHS)
        ├──► superspace/district_graph.py (node lambda_vacuum)
        ├──► radon/vacuum_stream.py (stream scaling)
        └──► observatory/filters/string_filter.py (W_string)
```

---

## Related documents

- [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md) — Equations 1, 8
- [VARIATIONAL_PRINCIPLE.md](./VARIATIONAL_PRINCIPLE.md) — $\mathcal{L}_{\text{string}}$
- [RADON_VACUUM_PIPELINE.md](./RADON_VACUUM_PIPELINE.md) — stream scaling by $\Lambda$
- [NOTATION.md](./NOTATION.md)
