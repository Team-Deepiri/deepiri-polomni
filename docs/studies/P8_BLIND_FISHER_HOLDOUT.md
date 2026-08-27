# P8 — Blind Fisher Holdout + Denser-Tracer Forecast

**Study extension:** P5-RDF Phase G  
**Modules:** `blind_fisher_holdout.py`, `dense_tracer.py`  
**Command:** `poetry run polomni data rdf-tomography`

---

## Locksmith reframe

| Old wall | New question |
|----------|--------------|
| Maximize Fisher on Planck then claim | Look-elsewhere + peeking |
| Wait for ACT×DESI TB download | Forecast √(N·f_sky) scaling now; stack cached tracers |
| **New protocol** | **Freeze axis on WMAP K; test SNR at that axis on Planck only** |

---

## Mathematics / protocol

1. **Train:** Fisher max axis on WMAP K × PSCz (axis selection only).
2. **Freeze** û_train — never re-maximize on Planck for the gate statistic.
3. **Holdout:** SNR(û_train) on Planck SMICA × PSCz.
4. **Null:** galaxy shuffle; same frozen axis on Planck.
5. **Forecast:** SNR_DESI ≈ SNR_now · √[(N_DESI/N_now)·(f_DESI/f_now)].

**Gate:** p_holdout < 0.01, holdout SNR > 1, train SNR > 0.5.

---

## Honest status

| Claim | Status |
|-------|--------|
| Blind holdout protocol implemented | **Yes** |
| WMAP→Planck bubble detection today | **Expected null** |
| Multiverse ruled out | **No** — forecast may still clear SNR>2 with DESI-class N |

---

## Next

1. ~~Ingest public DESI LRG / ACT DR6 cross-match~~ → **P9** SDSS LRG-dense (DESI file pending)
2. Tier **`bubble_visible`** when Phase G/H gate passes on holdout
