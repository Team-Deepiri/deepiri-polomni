# CMB Data Pipeline

End-to-end guide for loading CMB maps, computing the **RBLE signature** $\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})$, and producing falsification reports.

**Theory:** [../theory/CMB_OBSERVATORY_MATH.md](../theory/CMB_OBSERVATORY_MATH.md) · **Predictions:** [../theory/FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md)

---

## Overview

```
FITS/HEALPix  →  ingest  →  filter  →  score  →  null compare  →  report
```

Implementation: `src/polomni/observatory/`

---

## CLI Scan

### Synthetic map (smoke test)

```bash
poetry run polomni scan --synthetic --nside 64 --seed 0 --null-ensemble 100
```

### Real map file

```bash
poetry run polomni scan \
  --map /path/to/cmb_map.fits \
  --field T \
  --nside 512 \
  --null-ensemble 1000 \
  --output report.json
```

| Flag | Description |
|------|-------------|
| `--map` | Path to FITS HEALPix file |
| `--synthetic` | Generate Gaussian random CMB instead |
| `--field` | `T`, `Q`, or `U` |
| `--nside` | HEALPix resolution |
| `--null-ensemble` | Number of null maps for $p$-value |
| `--W-params` | JSON flux integers for string filter |
| `--output` | Detection report JSON path |

---

## Python Pipeline

### Step 1 — Load map

```python
from polomni.observatory.ingest.healpix_loader import load_healpix_map, synthetic_cmb_map

# Real data
T_map = load_healpix_map("planck_dr3_temperature.fits", field="T")

# Or synthetic null
T_map = synthetic_cmb_map(nside=128, seed=42)
```

### Step 2 — Polarization (optional, for $T$–$E$ test)

```python
from polomni.observatory.ingest.polarization import extract_qu_maps

Q_map, U_map = extract_qu_maps(T_map)  # or load Q/U from separate files
```

### Step 3 — String landscape filter

```python
from polomni.observatory.filters.string_filter import string_landscape_filter

W_params = {"flux_integers": [1, 0, -1, 2]}
T_filtered = string_landscape_filter(T_map, W_params)
```

Applies $\mathbf{W}_{\text{string}}(\Lambda(W,K))$ weighting:

$$
\mathcal{R}_{S^2}\!\left[\frac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}\right]
$$

### Step 4 — Inverse Radon–bifurcation filter

```python
import numpy as np
from polomni.observatory.filters.radon_bifurcation import inverse_radon_bifurcation_filter

angles = np.linspace(0, 2 * np.pi, 36, endpoint=False)
radon_stack = inverse_radon_bifurcation_filter(T_filtered, angles)
```

Uses geodesic Radon on $S^2$:

$$
\mathcal{R}_{S^2}[f](\hat{\mathbf{n}}, \eta) = \int_{\gamma(\hat{\mathbf{n}},\eta)} f\, dl
```

Core transform: `src/polomni/core/radon/transform_s2.py::radon_transform_s2`

### Step 5 — RBLE signature score

```python
import numpy as np
from polomni.observatory.scoring.rble_signature import compute_rble_signature, DetectionReport

n_hat = np.array([0.0, 0.0, 1.0])  # scan axis
score = compute_rble_signature(T_filtered, n_hat)

# Full sky search (coarse)
# iterate over HEALPix pixel directions
```

Signature functional:

$$
\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})
= \int_0^{2\pi}
\mathbf{M}(\alpha)\cdot \mathcal{R}_{S^2}\!\left[\frac{\Delta T}{T} \otimes \mathbf{W}_{\text{string}}\right]
(\hat{\mathbf{n}}, \alpha)\, d\alpha
$$

### Step 6 — Null ensemble comparison

```python
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble

null_scores = []
for null_map in generate_null_ensemble(n_maps=1000, nside=128, seed=123):
    null_scores.append(compute_rble_signature(null_map, n_hat))

import numpy as np
p_value = (1 + sum(s >= score for s in null_scores)) / (len(null_scores) + 1)
```

### Step 7 — Detection report

```python
from polomni.observatory.reports.detection_report import format_report, save_report

report = DetectionReport(
    rble_score=float(score),
    preferred_axis=tuple(n_hat.tolist()),
    p_value_null=float(p_value),
    falsification_flags={
        "p1_radon_scar": "pass" if p_value < 0.01 else "fail",
        "p2_clustered_fnl": "inconclusive",
        "p3_gw_ringdown": "inconclusive",
        "surviving_layers": ["conservation", "radon_pipeline"],
    },
)

print(format_report(report))
save_report(report, "detection_report.json")
```

---

## Synthetic Scar Injection Test

Validate recovery before real data:

```python
import numpy as np
import healpy as hp
from polomni.observatory.scoring.rble_signature import compute_rble_signature

nside = 64
npix = hp.nside2npix(nside)
T_map = np.random.randn(npix) * 1e-5  # background

# Inject scar at north pole
n_inj = np.array([0.0, 0.0, 1.0])
theta, phi = hp.pix2ang(nside, np.arange(npix))
vec = np.array(hp.pix2vec(nside, np.arange(npix))).T
cos_angle = vec @ n_inj
T_map += 1e-4 * np.exp(-((1 - cos_angle) ** 2) / 0.01)

score = compute_rble_signature(T_map, n_inj)
assert score > 0  # see tests/observatory/test_rble_signature.py for full criteria
```

---

## Hierarchical Sky Search

For NSIDE $\geq 512$, do not scan all pixels blindly:

1. **Coarse pass** — NSIDE=64, keep top-10 axes by $\mathcal{S}_{\text{RBLE}}$
2. **Refine** — NSIDE=512 in $10°$ cones around candidates
3. **Final** — NSIDE=2048 for best axis only

Apply Bonferroni correction:

$$
p_{\text{corrected}} = \min(1,\; N_{\text{tests}} \cdot p_{\text{raw}})
$$

---

## Visualization

```python
from polomni.viz.sky_map import plot_mollweide

plot_mollweide(
    T_map,
    title="CMB with RBLE scar candidate",
    highlight_axis=n_hat,
    save_path="sky_overlay.png",
)
```

---

## Neural Pre-Screen (Optional)

Fast approximate scoring before deterministic pipeline:

```python
from polomni.neural.scar_classifier.rble_scanner import score_map

approx = score_map(T_map)  # requires poetry install -E torch
```

Use `rble_signature.py` for publication $p$-values.

---

## Data Sources

| Dataset | Notes |
|---------|-------|
| Planck PR3 | Temperature and polarization HEALPix FITS |
| WMAP | Lower resolution validation |
| Simons Observatory | Future high-sensitivity $Q,U$ |
| LiteBIRD | Future full-sky polarization |

Ensure maps are in thermodynamic temperature units ($\mu K$) or dimensionless $\Delta T/T$ consistently.

---

## Falsification Flags

Report must include P1 status per [FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md):

- **Pass:** $p < 0.01$ after correction AND injection recovery test passes
- **Fail:** consistent with null ensemble
- **Inconclusive:** insufficient null draws or resolution

---

## Related

- [getting_started.md](./getting_started.md)
- [running_simulations.md](./running_simulations.md)
- [../architecture/SYSTEM_OVERVIEW.md](../architecture/SYSTEM_OVERVIEW.md)
