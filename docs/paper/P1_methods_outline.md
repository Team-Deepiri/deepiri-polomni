# Paper 1 Methods — Outline (arXiv astro-ph.IM / JCAP)

**Working title:** *Radon-anisotropic CMB scar search with pre-registered axis statistics*

**Status:** Methods + calibration + **blind holdout executed** (2026-06-28). See `data/studies/p1_holdout/RESULT.json`.

---

## Abstract (draft)

We introduce a pre-registered search statistic \(\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})\) for anisotropic large-scale CMB features, implemented in the open Polomni pipeline. We define three null tiers (N0 GRF, N1 CAMB+noise, N2 rotation-shuffled), Bonferroni-corrected hierarchical axis search, injection recovery calibration, and a \(T\)–\(E\) correlation cross-check. We validate the pipeline on WMAP Ka-band calibration; a blind Planck SMICA holdout **falsifies P1** under the frozen protocol — demonstrating the analysis is empirically constrained, not post-hoc tuned.

---

## 1. Introduction

- Motivation: testable anisotropic CMB features beyond azimuthally symmetric templates  
- Relation to Axis of Evil / hemispherical asymmetry literature  
- **Claim scope:** methods + pre-registered falsification; not multiverse confirmation  
- Open replication: `make reproduce-p1`, `docs/REPLICATION.md`

## 2. Data

| Product | Mission | Role | URL (catalog) |
|---------|---------|------|---------------|
| WMAP Ka-band | WMAP 9yr | Calibration | `lambda.gsfc.nasa.gov` |
| Planck SMICA | Planck 2018 | **Blind holdout** | `irsa.ipac.caltech.edu` |
| Planck TT binned | Planck 2018 | N1 null \(C_\ell\) | IRSA DR3 |

Downloads: SHA256-verified cache (`data/cache/manifest.json`).

## 3. Statistic

- \(\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})\) — `rble_signature.py`, geodesic Radon on \(S^2\)  
- String landscape filter + Radon bifurcation filter (`string_filter.py`, `radon_bifurcation.py`)  
- Hierarchical coarse→fine axis search (`hierarchical_sky_search`)

## 4. Null models (N0, N1, N2 — shipped)

| Tier | Implementation | Module |
|------|----------------|--------|
| **N0** | Isotropic GRF ensemble | `generate_grf_null` |
| **N1** | Planck \(C_\ell\) + noise realizations | `generate_camb_noise_null` |
| **N2** | HEALPix rotation-shuffled map | `generate_rotation_shuffled_null` |

Bonferroni over declared search trials (`count_sky_search_tests`, \(\alpha=0.01\)).

## 5. Injection recovery (Gate 2)

- Synthetic scar at known axis on GRF  
- **Pass:** ≥90% trials recover axis within 5° at SNR≥3  
- Test: `tests/observatory/test_p1_injection_recovery.py`

## 6. Results

### 6.1 Calibration (WMAP Ka, NSIDE 128)

Run: `polomni study run p1 --calibration`

Pipeline validates on independent WMAP map; scores are recorded in `CALIBRATION_RESULT.json`.

### 6.2 Blind holdout (Planck SMICA, NSIDE 128)

Run: `polomni study run p1 --blind` (config frozen in `study_config.json` **before** holdout)

| Quantity | Holdout value |
|----------|---------------|
| \(S_{\text{RBLE}}\) | 1.130 |
| Bonferroni pass | **No** (ensemble null \(\sigma < 0\)) |
| N0 GRF \(p\) (Bonf.) | 0.032 × 36 > \(\alpha\) |
| N2 rotation \(p\) | 0.319 (not significant) |
| TE cross-check | **Fail** (\(\sigma \approx -0.09\)) |
| **P1 supported** | **false** |
| **P1 falsified** | **true** |

**Interpretation:** The pre-registered hypothesis is **not supported** on Planck holdout. This is a valid scientific outcome — the pipeline ingested real 384 MB Planck SMICA FITS and applied locked filters/search/nulls without peeking.

## 7. Discussion

- Falsification ≠ pipeline failure; it constrains RBLE CMB scar claims  
- TE check uses Q/U proxy; full Planck polarization likelihood needed for publication-grade TE  
- Independent replication (Gate 5) remains open  

## Appendix A — Code map

| Component | Module |
|-----------|--------|
| Study runner | `p1_runner.py` |
| Gates 1–4 | `gates.py` |
| Frozen config | `data/studies/p1_holdout/study_config.json` |
| Pre-registration | `docs/studies/P1_CMB_RADON_SCAR_PREREG.md` |
| Replication | `scripts/reproduce-p1.sh`, `docs/REPLICATION.md` |

## Replication checklist

- [x] Pre-registration before holdout  
- [x] N0/N1/N2 null tiers implemented  
- [x] Injection recovery test  
- [x] Blind Planck holdout executed  
- [x] `make reproduce-p1` one-shot replication  
- [x] Docker `reproduce` profile  
- [x] Gate 5 golden reference + `polomni study replicate`  
- [ ] Independent team replication (external Gate 5 sign-off)  
- [ ] Peer-reviewed submission (Gate 6)
