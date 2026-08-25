# P7 — Multi-z Fisher Tomography (Sensitivity Ladder)

**Study extension:** P5-RDF Phase F  
**Module:** `multi_z_tomography.py`  
**Command:** `poetry run polomni data rdf-tomography`

---

## Locksmith reframe

| Old wall | New question |
|----------|--------------|
| Single-z Phase E SNR~1.3, p~0.08 | Sensitivity floor of all-sky average |
| Wait for RemoteField vendor clone | PSCz already has Hvel → z |
| **New invariant** | **Same SO(2,1) axis across redshift shells + kernel-weighted Fisher stack** |

A true bubble collision axis is fixed on the sky through z. ΛCDM kSZ / shot noise axes wander. Stacking with radial kernel w(z)∝√N·z e^{-z/z_*} recovers forecast-like multi-bin gain without full SZ_cosmo.

---

## Mathematics

1. Split PSCz into z-shells (default edges 0 / 0.012 / 0.035 / 0.12).
2. Per shell: high-pass ΛCDM mitigation → MV quadratic → Fisher (corr₁, corr₂).
3. Stack: x̄ = Σ ŵ_i x_i ; SNR = x̄ · [A,B]̂.
4. Cross-z coherence: mean pairwise axis separation (small ⇒ candidate).
5. Null: shuffle sky positions; keep z-bin membership; re-stack.

**Gate:** p_snr<0.01, stacked SNR>1.5, all bins sign-coherent, pairwise sep<35°, p_coherence<0.05, RBLE scar within 25°.

---

## Honest status

| Claim | Status |
|-------|--------|
| Multi-z instrument recovers injected shared axis | **Unit-tested** |
| Planck×PSCz multi-z detection today | **Expected null / marginal** — still sensitivity-limited |
| Multiverse ruled out | **No** |

---

## Next ladder rungs

1. ~~ACT×DESI-class tracer ingest~~ → forecast + PSCz+SDSS stack (**P8**)
2. ~~Blind holdout: WMAP train → Planck test~~ → **P8 / Phase G**
3. Optional vendor RemoteField / SZ_cosmo kernels
4. Tier **`bubble_visible`** when Phase G gate passes on denser tracers
5. Public DESI LRG ingest (real N, not forecast)
