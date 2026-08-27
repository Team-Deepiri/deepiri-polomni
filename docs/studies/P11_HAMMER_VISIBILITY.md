# P11 — Hammer Visibility (PSCz ∪ NVSS ∪ mega-SDSS)

**Phase I** · `hammer_fisher.py` · `polomni data hammer-fisher`

Northern SDSS alone diluted Fisher (Phase H). **NVSS bright** (S≥200 mJy) is
all-sky-ish — stack with PSCz + mega SpecObj strips and re-measure. Also report
**PSCz∪NVSS** (no SpecObj) so SpecObj dilution is isolated.

| Gate | Same as Fisher E/H |
|------|---------------------|
| Win condition | SNR > PSCz **and** approaching 2 with p<0.01 |

## Real-sky result (2026-08-25)

| Stack | N | SNR | Notes |
|-------|---|-----|-------|
| PSCz | 18 351 | **1.28** | Best public stack |
| PSCz∪NVSS | 43 070 | 1.24 | Near-PSCz; mild dilution |
| PSCz∪NVSS∪mega-SDSS | 60 503 | 0.93 | SpecObj dilutes hard |
| DESI LRG-class forecast | ≥1e5 | ~9.7 | From PSCz baseline √N |

**Verdict:** Gate fail. Public densification (NVSS + SpecObj) does **not** beat
PSCz Fisher SNR. Visibility remains **not ruled out**; blocked on DESI-class
all-sky dense tracers.

See P10 for DESI resource needs.
