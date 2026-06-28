# CMB Observatory Mathematics

Mathematical specification for detecting **RBLE Radon scars** on the cosmic microwave background — geodesic Radon transform on $S^2$, inverse bifurcation filter, and detection statistics.

**Master equation:** Equation 6 in [RBLE_MASTER_EQUATIONS.md](./RBLE_MASTER_EQUATIONS.md). **Falsification:** Prediction P1 in [FALSIFICATION_CRITERIA.md](./FALSIFICATION_CRITERIA.md). **Implementation:** `omnifold_observatory/`.

---

## Observable Hypothesis

If our universe nucleated from a parent **Radon data stream**, the injection event imprints an anisotropic, string-filtered signature on the CMB — not a generic circular bubble-collision disc.

| Feature | Standard bubble collision | RBLE Radon scar |
|---------|---------------------------|-----------------|
| Symmetry | Azimuthally symmetric disc | **Anisotropic ring** |
| Polarization | Primarily temperature | **$T$–$E$ coupling** via $\mathbf{M}(\alpha)$ |
| Harmonics | Low $\ell \sim 2$–$5$ | **$\ell$-mode ladder** from SO(3) |
| Orientation | Random | **Locked to** $\hat{\mathbf{n}}_0$ |
| Filter | None | **$\mathbf{W}_{\text{string}}(\Lambda(W,K))$** |

---

## CMB Fields on $S^2$

### Temperature

$$
\frac{\Delta T}{T}(\hat{\mathbf{r}}), \quad \hat{\mathbf{r}} \in S^2
$$

### Polarization (Stokes)

$$
Q(\hat{\mathbf{r}}), \quad U(\hat{\mathbf{r}})
$$

Spin-2 decomposition:

$$
(Q \pm iU)(\hat{\mathbf{r}})
= \sum_{\ell m} a_{\ell m}^{E} Y_{\ell m}^{E}(\hat{\mathbf{r}})
+ a_{\ell m}^{B} Y_{\ell m}^{B}(\hat{\mathbf{r}})
$$

**Code:** `omnifold_observatory/ingest/polarization.py::extract_qu_maps`

### HEALPix discretization

Pixel index $p \in \{0, \ldots, 12\,N_{\text{side}}^2 - 1\}$ with equal-area pixels.

**Code:** `omnifold_observatory/ingest/healpix_loader.py::load_healpix_map`, `synthetic_cmb_map(nside, seed)`

---

## Spherical Radon Transform

### Geodesic line integral

$$
\mathcal{R}_{S^2}[f](\hat{\mathbf{n}}, \eta)
= \int_{\gamma(\hat{\mathbf{n}},\,\eta)} f(\hat{\mathbf{r}})\, dl
$$

- $\hat{\mathbf{n}}$ — unit vector normal to great circle (scan axis)
- $\gamma(\hat{\mathbf{n}}, \eta)$ — geodesic arc at offset $\eta$
- $dl$ — line element on $S^2$

### Discrete chord integration

Along HEALPix ring at constant colatitude relative to $\hat{\mathbf{n}}$:

$$
\mathcal{R}_{S^2}[f](\hat{\mathbf{n}}, \eta_j)
\approx \sum_{k \in \text{ring}(\eta_j)} w_k\, f_k\, \Delta l_k
$$

**Code:** `omnifold_core/radon/transform_s2.py::radon_transform_s2(healpix_map, n_hat, eta)`

---

## RBLE Sky Signature

### String-filtered Radon score

$$
\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
= \int_0^{2\pi}
\left[
\mathbf{M}(\alpha)\cdot
\mathcal{R}_{S^2}\!\left[
\frac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}
\right]
(\hat{\mathbf{n}}, \alpha)
\right] d\alpha
$$

### String landscape filter

$$
\mathbf{W}_{\text{string}} = \mathbf{W}(\Lambda(W,K), \{n_I\})
$$

Applied as multiplicative harmonic-space mask or pixel-space convolution.

**Code:** `omnifold_observatory/filters/string_filter.py::string_landscape_filter(map, W_params)`

### Inverse Radon–bifurcation filter

Reconstructs candidate injection surface from ring stack:

$$
\hat{f}_{\text{inj}}(\hat{\mathbf{r}})
= \mathcal{R}_{S^2}^{-1}\!\left[
\arg\max_{\hat{\mathbf{n}}} \mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
\right]
$$

Discrete implementation: filtered back-projection over angle ensemble $\{\alpha_i\}$.

**Code:** `omnifold_observatory/filters/radon_bifurcation.py::inverse_radon_bifurcation_filter(map, angles)`

---

## Detection Statistics

### Maximum axis statistic

$$
S_{\max} = \max_{\hat{\mathbf{n}} \in \mathcal{A}} \mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
$$

where $\mathcal{A}$ is the set of HEALPix pixel directions (or reduced icosahedral set for speed).

### Null ensemble

Under $H_0^{(1)}$ (isotropic $\Lambda$CDM):

$$
S_{\max}^{(b)} \sim \mathcal{F}_{\text{null}}, \quad b = 1, \ldots, N_{\text{null}}
$$

**Code:** `omnifold_observatory/scoring/null_ensemble.py::generate_null_ensemble(n_maps, nside, seed)`

Generate $N_{\text{null}} \geq 10^4$ maps with same $C_\ell^{TT}$ as fiducial cosmology, no injected scar.

### $p$-value

$$
p = \frac{1}{N_{\text{null}} + 1}
\left(
1 + \sum_{b=1}^{N_{\text{null}}} \mathbf{1}\left[S_{\max}^{(b)} \geq S_{\max}^{\text{obs}}\right]
\right)
$$

### $T$–$E$ correlation along preferred axis

Given detected axis $\hat{\mathbf{n}}_0$:

$$
\rho_{TE}(\hat{\mathbf{n}}_0)
= \frac{
\int w(\hat{\mathbf{r}})\, (\Delta T/T)(\hat{\mathbf{r}})\, E(\hat{\mathbf{r}})\, d\Omega
}{
\sqrt{\int w^2 (\Delta T/T)^2}\,
\sqrt{\int w^2 E^2}
}
$$

with window $w$ centered on $\hat{\mathbf{n}}_0$ (Gaussian, FWHM $\sim 10°$).

### Detection report

**Code:** `omnifold_observatory/scoring/rble_signature.py`

```python
compute_rble_signature(map, n_hat) -> float
DetectionReport(
    rble_score: float,
    preferred_axis: tuple[float, float, float],
    p_value_null: float,
    falsification_flags: dict,
)
```

**Code:** `omnifold_observatory/reports/detection_report.py::format_report`, `save_json`

---

## Signal-to-Noise and Injection Tests

### Synthetic scar injection

Inject known Radon profile at axis $\hat{\mathbf{n}}_{\text{inj}}$:

$$
\left(\frac{\Delta T}{T}\right)_{\text{inj}}(\hat{\mathbf{r}})
= A \cdot \mathcal{G}(\hat{\mathbf{r}} \cdot \hat{\mathbf{n}}_{\text{inj}}; \sigma_{\text{scar}})
$$

$$
\mathcal{G}(u; \sigma) = \exp\!\left(-\frac{(1-u)^2}{2\sigma^2}\right)
$$

Recovery criterion (CI gate in `tests/observatory/test_rble_signature.py`):

$$
\arccos(\hat{\mathbf{n}}_0 \cdot \hat{\mathbf{n}}_{\text{inj}}) < 5°
\quad\text{at}\quad \text{SNR} \geq 3
$$

### SNR definition

$$
\text{SNR} = \frac{S_{\max}^{\text{obs}} - \mu_{\text{null}}}{\sigma_{\text{null}}}
$$

where $\mu_{\text{null}}, \sigma_{\text{null}}$ from null ensemble.

---

## Multiple Comparison Correction

Testing all $\sim N_{\text{pix}}$ axes requires Bonferroni or FDR control:

$$
p_{\text{corrected}} = \min\!\left(1,\; N_{\text{tests}} \cdot p_{\text{raw}}\right)
$$

At NSIDE=2048, $N_{\text{pix}} \approx 5 \times 10^7$ — use hierarchical search:

1. Coarse scan at NSIDE=64
2. Refine top-$K$ candidates at NSIDE=512
3. Full resolution at NSIDE=2048 for final $K \leq 10$ axes

---

## Harmonic Pipeline (Alternative)

Spin-2 harmonic domain equivalent:

$$
a_{\ell m}^{\text{filtered}}
= \sum_{\ell' m'} \mathcal{M}_{\ell m,\ell' m'}^{\mathbf{W}_{\text{string}}}
a_{\ell' m'}^{\text{obs}}
$$

Radon score computed on filtered map. Equivalent to pixel pipeline at full resolution.

---

## Data Flow

```
FITS / HEALPix file
    │
    ▼  healpix_loader.load_healpix_map
T_map (and optional Q, U)
    │
    ▼  polarization.extract_qu_maps
Q_map, U_map
    │
    ▼  string_filter.string_landscape_filter
T_filtered
    │
    ▼  radon_bifurcation.inverse_radon_bifurcation_filter
Radon stack R_S²[T](n̂, α)
    │
    ▼  rble_signature.compute_rble_signature
S_RBLE(n̂), DetectionReport
    │
    ▼  null_ensemble comparison
p-value, falsification_flags.p1_radon_scar
    │
    ▼  detection_report.format_report
JSON + Mollweide overlay (visualization/sky_map.py)
```

---

## CLI Entry Point

```bash
omnifold scan --map path/to/cmb.fits --nside 512 --null-ensemble 1000
```

See [../guides/cmb_data_pipeline.md](../guides/cmb_data_pipeline.md).

---

## Neural Acceleration (Optional)

`omnifold_neural/scar_classifier/rble_scanner.py::score_map` provides fast approximate $\mathcal{S}_{\text{RBLE}}$ for survey-scale screening. Final detection must use deterministic `rble_signature.py` for publication-grade $p$-values.

---

## Related documents

- [FALSIFICATION_CRITERIA.md](./FALSIFICATION_CRITERIA.md) — P1 thresholds
- [RADON_VACUUM_PIPELINE.md](./RADON_VACUUM_PIPELINE.md) — $\mathbb{R}^3$ pipeline origin
- [STRING_LANDSCAPE_COUPLING.md](./STRING_LANDSCAPE_COUPLING.md) — $\mathbf{W}_{\text{string}}$
- [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md)
