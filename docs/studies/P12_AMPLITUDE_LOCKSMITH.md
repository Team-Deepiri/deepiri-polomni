# P12 — Amplitude Locksmith (past the Pearson wall)

**Phase J** · `amplitude_locksmith.py` · `polomni data amplitude-locksmith`

## 1. Reframe

Phases H–I asked for more galaxies. Pearson `corr(F, P_ℓ)` lives in **[-1, 1]**,
so Fisher SNR was hard-capped ≲ √2. More N cannot push amplitude through that
ceiling — the wall was the estimator, not the sky.

## 2. Outsider loop

1. Noise-normalized matched-filter `γ = (F·P) / (σ_F ‖P‖)`
2. Score at the **frozen RBLE scar axis** (no sky-max → no look-elsewhere floor)
3. WMAP×Planck coadd + **inject ladder** to prove the amplitude path reaches gate

## 3. System fix

Always report matched-filter beside Pearson. Real-sky gate rides **fixed-axis**
MF. Inject ladder records `min_amp` that clears the gate on the same estimator.

| Gate (real sky) | fixed-axis excess_z > 2, null_ratio ≥ 1.15, p ≤ 0.05 |
|-----------------|--------------------------------------------------------|
| Path proven | inject ladder finds Amin with gate_pass |
| Metric | M18 |

## Real-sky (honest)

Sky-max MF SNR ~230 is **not** a detection — proper PSCz nulls sit at ~223
(null_ratio≈1.04). Fixed-axis + inject ladder are the locksmith path.
