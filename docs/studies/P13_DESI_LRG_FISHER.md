# P13 — DESI LRG Fisher (SOTA lever)

**Phase K** · `desi_lrg_fisher.py` · `polomni data desi-lrg-fisher`

## SOTA math (required reading)

**Cai, Zhang, Guan (2025)** — [arXiv:2510.12134](https://arxiv.org/abs/2510.12134)
*Eternal inflation bubble collision signature on CMB remote dipole and quadrupole fields*

| Claim | Implication for Polomni |
|-------|-------------------------|
| Bubble collision has **SO(2,1)** symmetry | Only **m=0** RDF (ℓ=1) + RQF (ℓ=2) in collision frame — our Fisher template |
| Primordial potential ≈ linear **A** + quadratic **B** | Template ratio A:B (we use A=1, B=0.65 class) |
| RDF/RQF via quadratic estimator on CMB×galaxies | Same ACT×DESI LRG path already demonstrated in data [26] |
| **Tomography** across electron redshift bins | Multi-z stack mitigates ΛCDM variance (optimistic Fig. 7) |
| RQF alone ~**10×** primary-CMB constraints (CMB-S4×LSST forecast) | Dense LRG depth is the real lever, not more SpecObj strips |

Public tool: **RemoteField** (Cai et al.) + **SZ_cosmo** kernels.

## Data (this phase)

DESI Guadalupe VAC clustering (first 2 months main survey, public):

```
https://data.desi.lbl.gov/public/dr1/vac/dr1/lss/guadalupe/v1.0/LSScats/clustering/
LRG_N_clustering.dat.fits   (~81k)
LRG_S_clustering.dat.fits   (~181k)
```

Total **N ≈ 2.6×10⁵**, z ∈ [0.4, 1.1]. Full iron DR1 LSS is the next scale-up (~10⁶).

## Gate

Same visibility bar as P10 (SNR>2, p<0.01, coherent, optional cross-z <35°).
Metric **M19**.

## Real-sky (2026-08-25)

| Stack | N | SNR |
|-------|---|-----|
| PSCz | 18 351 | **1.28** |
| DESI Guadalupe LRG | **261 291** | 1.25 |
| Multi-z stack (0.4/0.6/0.8/1.1) | — | 1.25 |
| √N expected ratio | 3.77× | observed **0.97×** — scaling fails |
| Full-DR1 forecast | — | ~2.6 (if amplitude real) |

**Verdict:** Gate fail. Public DESI LRG densification does **not** raise Pearson Fisher above PSCz — consistent with Phase H/I dilution / noise-dominated imprint. Visibility still **not ruled out**; next SOTA levers are (1) fixed-axis matched-filter on DESI shells (Phase J×K), (2) full iron DR1 LSS, (3) ACT kSZ×DESI quadratic estimator closer to Cai RemoteField.
