# Paper 1 Methods — Outline (arXiv astro-ph.IM / JCAP)

**Working title:** *Radon-anisotropic CMB scar search with pre-registered axis statistics*

**Not a discovery paper.** Submit after injection recovery + null hierarchy validated; holdout results go in Paper 1b.

---

## Abstract (draft)

We introduce a pre-registered search statistic \(\mathcal{S}_{\text{RBLE}}(\hat{\mathbf{n}})\) for anisotropic large-scale CMB features motivated by stream-injection models, implemented in the open Polomni pipeline. We define three null tiers (GRF, CAMB+noise, rotation-shuffled), Bonferroni-corrected axis search, injection recovery calibration, and a \(T\)–\(E\) correlation cross-check. We validate the pipeline on WMAP Ka-band; Planck SMICA holdout analysis is pre-registered separately.

---

## 1. Introduction

- Motivation: anisotropic CMB features beyond azimuthally symmetric bubble collisions  
- Relation to existing searches (Hemisphere power asymmetry, Axis of Evil literature)  
- **Claim scope:** methods + calibration; not "multiverse confirmed"  
- Polomni / RBLE as open reproducible framework  

## 2. Data

| Product | Mission | Role |
|---------|---------|------|
| WMAP Ka-band | WMAP 9yr | Calibration |
| Planck SMICA | Planck 2018 | Holdout (pre-registered) |
| Planck TT binned | Planck 2018 | N1 null Cl |

Cite: Bennett et al., Planck Collaboration papers. URLs from `pipeline/catalog.py`.

## 3. Statistic

- Define \(\mathcal{S}_{\text{RBLE}}\) (Eq. 6) — ref [CMB_OBSERVATORY_MATH.md](../theory/CMB_OBSERVATORY_MATH.md)  
- String landscape filter + Radon bifurcation filter  
- Hierarchical axis search  

## 4. Null models

- N0 GRF (`generate_null_ensemble`)  
- N1 CAMB+noise (`generate_camb_noise_null`)  
- N2 rotation-shuffled (`generate_rotation_shuffled_null`)  
- Bonferroni over declared search trials  

## 5. Injection recovery

- Synthetic scar on GRF at known axis  
- ROC: detection rate vs axis error vs SNR  
- Pass criterion: 90% @ SNR≥3, error < 5°  

## 6. Calibration run (WMAP)

- Report \(S_{\max}\), axis, null tier \(p\)-values  
- **No discovery language**  

## 7. Discussion

- Look-elsewhere effect limits  
- TE proxy limitations (full Planck Q/U maps needed for publication-grade TE)  
- What would falsify the statistic  

## Appendix A — Code map

| Equation | Module |
|----------|--------|
| Eq. 6 | `rble_signature.py`, `transform_s2.py` |
| Filters | `string_filter.py`, `radon_bifurcation.py` |
| Study | `p1_runner.py`, `study_config.json` |

## Current gaps (honest)

- [ ] Holdout not yet run at time of methods draft  
- [ ] TE check is proxy, not full Planck polarization likelihood  
- [ ] N1 depends on cache availability  
