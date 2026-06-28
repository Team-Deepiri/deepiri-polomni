# Pre-Registration: P1 CMB Radon Scar Search

**Study ID:** `p1_cmb_radon_scar`  
**Version:** `1.0.0`  
**Registered:** 2026-06-28  
**Status:** Registered **before** any holdout analysis on Planck SMICA  

**Master playbook:** [PHYSICS_ESTABLISHMENT.md](../PHYSICS_ESTABLISHMENT.md)  
**Hypothesis definition:** [FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md) (Prediction P1)  
**Frozen config:** `data/studies/p1_holdout/study_config.json`  
**Git tag (after merge):** `study-p1-v1.0`

---

## 1. Primary hypothesis

There exists a preferred axis \(\hat{\mathbf{n}}_0\) on the real CMB sky such that the Radon-anisotropic, string-filtered statistic \(\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})\) (Eq. 6) exceeds the distribution from:

1. **N0** — Gaussian random field (GRF) realizations matching the analysis NSIDE  
2. **N1** — CAMB \(\Lambda\)CDM + noise realizations (when cache available)  
3. **N2** — Rotation-shuffled maps (preserved pixel values, destroyed axis structure)

…after **Bonferroni correction** over declared search trials, **and** a \(T\)–\(E\) correlation check along \(\hat{\mathbf{n}}_0\) exceeds the null by \(\geq 3\sigma\).

**Alternative \(H_A^{(1)}\):** \(S_{\max} > S_{\text{threshold}}\) with TE coupling (see FALSIFICATION_CRITERIA).

**Null \(H_0^{(1)}\):** \(\mathcal{S}_{\text{RBLE}}\) is flat across axes; no preferred Radon-anisotropic scar.

---

## 2. Frozen analysis parameters

| Parameter | Value | Code |
|-----------|-------|------|
| Calibration map | WMAP 9yr Ka-band (`wmap_k_band`) | pipeline catalog |
| Holdout map | Planck 2018 SMICA (`planck_smica_cmb`) | **locked until blind run** |
| Search NSIDE | 128 | `study_config.json` |
| Confirmation NSIDE | 256 | optional post-holdout |
| Search method | Hierarchical coarse→fine | `hierarchical_sky_search` |
| Coarse NSIDE | 16 | |
| Coarse scan angles | 12 | |
| Refine cone | 15° | |
| Refine samples | 24 | |
| RNG seed | 0 | |
| String filter \(\beta\) | 0.15 | `string_landscape_filter` |
| String modes | \(m=2, n=1\) | frozen in config |
| Radon bifurcation angles | 2 triples | frozen in config |
| Null ensemble size | 30 per tier | |
| Bonferroni \(\alpha\) | 0.01 | two-sided |
| TE threshold | 3σ vs axis-shuffled null | `te_correlation_along_axis` |

**No parameter may be tuned using holdout map pixels before the one-shot blind run is written to `RESULT.json`.**

---

## 3. Prerequisites (must pass before holdout)

### 3.1 Injection recovery (Gate 2)

On GRF maps at NSIDE ≥ 32, synthetic Radon scar injected at known \(\hat{\mathbf{n}}_{\text{inj}}\):

| SNR (amplitude proxy) | Required detection rate | Max axis error |
|----------------------|-------------------------|----------------|
| ≥ 3 | ≥ 90% of trials | < 5° |

**Test:** `tests/observatory/test_p1_injection_recovery.py`  
**Notebook:** `experiments/17_p1_injection_calibration.ipynb`

Holdout analysis is **invalid** if injection recovery fails at SNR ≥ 3.

### 3.2 Null tier implementation (Gate 3)

All three tiers implemented in `null_models.py` and reported in `polomni study run p1`.

---

## 4. Holdout protocol (Gate 4)

1. Run `polomni study run p1 --calibration` on WMAP — pipeline validation only  
2. Run `polomni study run p1 --blind` on Planck SMICA — **one shot**  
3. Write `data/studies/p1_holdout/RESULT.json` with `blind: true`, git SHA, config version  
4. No code or filter changes between steps 2 and publication draft  

---

## 5. Pass / fail criteria (holdout)

**P1 SUPPORTED** if and only if all hold:

| Criterion | Threshold |
|-----------|-----------|
| Bonferroni-corrected \(p\) vs N0 | < 0.01 |
| Bonferroni-corrected \(p\) vs N1 | < 0.01 |
| Bonferroni-corrected \(p\) vs N2 | < 0.01 |
| TE correlation along \(\hat{\mathbf{n}}_0\) | > null mean + 3σ |
| Injection recovery (prerequisite) | PASS |

**P1 FALSIFIED** if any null tier fails at corrected \(p > 0.01\) **or** TE check fails.

**INCONCLUSIVE** if holdout map not cached or N1 unavailable (must be stated in paper; not a discovery).

---

## 6. What would falsify RBLE sky layer

- Holdout fails all three null tiers after correction  
- TE coupling absent along recovered axis  
- Injection recovery fails at declared SNR  
- Preferred axis unstable under NSIDE 128 → 256 confirmation  
- Signal tracks known instrumental systematic (e.g. dipole subtraction artifact) — requires manual review figure  

RBLE **core layers** (conservation, district simulator, directed diffusion EFT) may survive per FALSIFICATION_CRITERIA survival table.

---

## 7. Analysis code pins

| Component | Module |
|-----------|--------|
| Statistic | `polomni.observatory.scoring.rble_signature` |
| Search | `polomni.observatory.scoring.hierarchical_search` |
| Nulls | `polomni.observatory.scoring.null_models` |
| Study runner | `polomni.observatory.studies.p1_runner` |
| CLI | `polomni study run p1` |

Record `git rev-parse HEAD` in every `RESULT.json`.

---

## 8. Registration attestation

This document and `study_config.json` v1.0.0 were committed **before** the first Planck SMICA holdout run logged to `RESULT.json`.

Authors: Deepiri Polomni team  
Contact: research@deepiri.ai
