# Paper 1b Results — Template (fill after blind holdout)

**Run:** `polomni study run p1 --blind`  
**Prereg:** [P1_CMB_RADON_SCAR_PREREG.md](../studies/P1_CMB_RADON_SCAR_PREREG.md)  
**Git SHA:** `{{ GIT_SHA }}`  
**Date:** `{{ RUN_DATE }}`

---

## Summary table

| Quantity | Value |
|----------|-------|
| Map | Planck SMICA |
| NSIDE | 128 |
| \(S_{\max}\) | {{ RBLE_SCORE }} |
| Preferred axis \(\hat{n}\) | [{{ NX }}, {{ NY }}, {{ NZ }}] |
| Bonferroni \(N_{\text{tests}}\) | {{ N_TESTS }} |
| Bonferroni pass | {{ BONF_PASS }} |

---

## Null tier \(p\)-values (before/after Bonferroni)

| Tier | Raw \(p\) | Corrected pass @ \(\alpha=0.01\) |
|------|-----------|----------------------------------|
| N0 GRF | {{ P_GRF }} | {{ PASS_GRF }} |
| N1 CAMB+noise | {{ P_CAMB }} | {{ PASS_CAMB }} |
| N2 rotation-shuffled | {{ P_ROT }} | {{ PASS_ROT }} |

---

## TE correlation

| Metric | Value |
|--------|-------|
| \(\rho_{TE}(\hat{n}_0)\) | {{ TE_RHO }} |
| Null mean | {{ TE_NULL_MU }} |
| Significance (σ) | {{ TE_SIGMA }} |
| Pass (≥ 3σ) | {{ TE_PASS }} |

---

## Falsification matrix

| P1 | P2 | P3 | Verdict |
|----|----|----|---------|
| {{ P1 }} | inconclusive | inconclusive | {{ VERDICT }} |

---

## Conclusion boilerplate

**If P1 supported:** We report a pre-registered excess in \(\mathcal{S}_{\text{RBLE}}\) on Planck SMICA after multi-tier null comparison and TE cross-check. Independent replication is required (see REPLICATION_P1.md).

**If P1 falsified:** We find no significant Radon-anisotropic scar after pre-registered correction. This falsifies the RBLE sky layer as stated in FALSIFICATION_CRITERIA; effective theory layers remain valid.

---

## Attach

- `data/studies/p1_holdout/RESULT.json` (supplementary)  
- Figure set from [FIGURES.md](./FIGURES.md)
