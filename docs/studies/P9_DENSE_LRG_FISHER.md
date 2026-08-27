# P9 — Dense LRG Fisher (Visibility Ladder)

**Study extension:** P5-RDF Phase H  
**Module:** `dense_lrg_fisher.py`  
**Command:** `poetry run polomni data dense-lrg-fisher`

---

## Locksmith reframe

| Old wall | New question |
|----------|--------------|
| Wait for multi-TB DESI LRG DR | Stratified SDSS SpecObj RA strips (public, LRG/CMASS-like z) |
| Forecast only | **Measure** Fisher on PSCz∪LRG and check √N scaling |

---

## Protocol

1. Fetch SDSS SpecObj `0.15<z<0.7` across 36 RA strips (dense LRG-class sample).
2. Stack with IRAS PSCz → denser all-sky-ish tracer.
3. Fisher SO(2,1) on Planck SMICA × dense δ vs PSCz-only baseline.
4. Compare SNR ratio to √(N_dense/N_pscz); forecast DESI-class N.

**Gate:** same as Phase E Fisher (p<0.01, SNR>2, coherent, scar align) — expected fail until true DESI depth.

---

## Honest status

| Claim | Status |
|-------|--------|
| Denser public tracer ingest | **Implemented** |
| Planck×dense LRG detection | **Expected null** |
| Multiverse works (instrument+ops) | **Still PROVEN** (M14+M15+M8+M9) |
| Multiverse ruled out | **No** |

---

## Next

1. Public DESI LRG catalog file ingest (when mirrored)
2. Tier **`bubble_visible`** when Phase G/H gate passes on holdout
