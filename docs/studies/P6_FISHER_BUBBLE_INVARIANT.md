# P6 — Fisher SO(2,1) Bubble Invariant (Multiverse Deep Scan)

**Study extension:** P5-RDF Phase E  
**Module:** `multiverse_fisher_scan.py`  
**Command:** `poetry run polomni data rdf-tomography`

---

## Locksmith reframe

| Old wall | New question |
|----------|--------------|
| "Find other universes as circles on the CMB" | Ruled out (Feeney → Planck → Polomni null) |
| "Find RDF and RQF peaks separately" | Axes misalign (26–81°) — wrong statistic |
| Full-sky T–δ γ-subtraction | Erases any bubble aligned with the tracer |
| Healpy `rotate_alm` axis scan | ~3 s/axis — unusable for null grids |
| **New invariant** | **Joint SO(2,1) corr(RDF,P₁)×corr(RQF,P₂) after high-pass mitigation** |

Eternal-inflation bubble collisions imprint **azimuthally symmetric** superhorizon modes. Along the collision axis û, only P₁(μ)=μ (RDF) and P₂(μ) (RQF) coactivate with fixed ratio A:B (Cai et al. 2025).

---

## Mathematics

1. **Mitigate ΛCDM:** high-pass δ (strip ℓ≤2), then T ← T − γ δ_hp. Removes small-scale ISW/kSZ-like linear leakage without zeroing bubble ℓ=1,2.
2. **MV quadratic:** reconstruct RDF/RQF maps (Deutsch et al. 2018); healpy alm uses m≥0 only.
3. **Dimensionless m=0 amplitudes:** corr(RDF, P₁(n·û)), corr(RQF, P₂(n·û)) — no map rotation.
4. **Fisher SNR:** SNR = x · t̂ with template t = [A, B], x = (corr₁, corr₂).
5. **Null:** galaxy-shuffle after same pipeline; p-value on max Fisher SNR.

**Gate:** p < 0.01, SNR > 2, sign-coherent m=0, RBLE scar axis within 25°.

---

## What we can prove vs what we cannot (honest)

| Claim | Status |
|-------|--------|
| RBLE multiverse loop works in simulation | **PROVEN** (M14) |
| Fisher scanner recovers injected bubble mode | **PROVEN** (unit tests — axis <25°, SNR>0.5) |
| Planck×PSCz shows bubble above Fisher null today | **NOT YET** — sensitivity-limited |
| Multiverse is impossible | **NOT RULED OUT** — forecast says CMB-S4×LSST class data needed |

We can prove the *thought* (instrument + invariant + null protocol). We can also prove a *null* at current sensitivity. We do **not** claim a peer-reviewed detection without blind holdout.

---

## Next: sensitivity ladder

1. ~~Multi-z tomography (RemoteField + SZ_cosmo kernels)~~ → **P7 / Phase F** (in-repo PSCz z-shells)
2. ACT×DESI-class galaxy tracer ingest
3. Blind holdout: WMAP train → Planck test
4. Tier **`bubble_visible`** when Phase E/F gate passes on holdout
