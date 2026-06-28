# Independent Replication — P1 CMB Radon Scar Study

Reproduce the pre-registered P1 analysis without reading Deepiri notebooks.

**Preregistration:** [P1_CMB_RADON_SCAR_PREREG.md](../studies/P1_CMB_RADON_SCAR_PREREG.md)  
**Config:** `data/studies/p1_holdout/study_config.json`

---

## 1. Requirements

- Python 3.10+, Poetry, `healpy`
- ~2 GB disk for WMAP Ka-band cache
- ~400 MB additional for Planck SMICA (holdout only)

---

## 2. Install

```bash
git clone https://github.com/Team-Deepiri/deepiri-polomni.git
cd deepiri-polomni
poetry install --with dev
```

Checkout tag `study-p1-v1.0` (after published) or commit matching prereg SHA.

---

## 3. Fetch data

```bash
# Calibration (required)
poetry run polomni data fetch wmap_k_band --no-lite --no-gw

# Holdout (blind run only)
poetry run polomni data fetch planck_smica_cmb --no-lite --no-gw

# Null tier N1 (optional but recommended)
poetry run polomni data fetch planck_cmb_tt_power camb_lcdm_cl --no-lite --no-gw
```

Verify:

```bash
poetry run polomni data status
```

---

## 4. Run study

### Calibration (WMAP — pipeline validation)

```bash
poetry run polomni study run p1 --calibration
# or: make reproduce-p1
```

### Blind holdout (Planck SMICA — one shot)

```bash
poetry run polomni study run p1 --blind
```

Output: `data/studies/p1_holdout/RESULT.json`

---

## 5. Expected `RESULT.json` schema

```json
{
  "study_id": "p1_cmb_radon_scar",
  "config_version": "1.0.0",
  "git_sha": "<40-char hex>",
  "mode": "calibration|holdout_blind",
  "blind": false,
  "map_product_id": "wmap_k_band",
  "nside": 128,
  "detection": { "rble_score": 0.0, "preferred_axis": [0,0,1], ... },
  "null_tier_comparison": { "tiers": { "grf": { "p_value": 0.0, ... } } },
  "bonferroni": { "n_tests": 36, "pass": true },
  "te_correlation": { "rho": 0.0, "sigma": 0.0, "pass": false },
  "p1_supported": false,
  "p1_falsified": false
}
```

---

## 6. Pass tolerances (replication agreement)

When re-running on the **same cache** and **same git SHA**:

| Field | Tolerance |
|-------|-----------|
| `detection.rble_score` | ± 0.05 |
| `detection.preferred_axis` | angular separation < 2° |
| `bonferroni.n_tests` | exact match |
| `null_tier_comparison.tiers.*.p_value` | ± 0.02 |

Different floating-point environments may widen score tolerance to ± 0.1.

**Fail replication if:** axis separation > 5° on same SHA/cache, or `p1_supported` flips without code change.

---

## 7. Injection recovery gate

Before trusting holdout:

```bash
poetry run pytest tests/observatory/test_p1_injection_recovery.py -q
```

Must pass at SNR ≥ 3 (≥ 90% trials, axis < 5°).

---

## 8. Report discrepancies

Open an issue with: git SHA, cache manifest checksum, full `RESULT.json`, and `polomni data status` output.
