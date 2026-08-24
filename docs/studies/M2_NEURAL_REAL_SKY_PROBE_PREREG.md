# M2 — Neural Real-Sky Multiverse Probe

**Study ID:** `m2_neural_real_sky_probe`  
**Status:** Active  
**Prereg:** 2026-08-24  
**Depends on:** Graph-NODE + scar checkpoints (`polomni neural train`)

---

## Claim (computational / interaction)

> On a frozen cached CMB product (default WMAP Ka), an **open-loop neural** closed
> loop (Graph-NODE guidance, **no** hard real-axis feedback) achieves **≥ 5° lower**
> final separation to the hierarchical preferred axis than **open-loop uniform**.

Physics-loop arms (with observational feedback) are logged for telemetry; they often
saturate near ~4–5° and are **not** the win criterion.

## Explicitly not claimed

- That other universes are detected in the CMB
- That P1 Radon scar survives (it was **falsified**)
- That agreement with a preferred axis = multiverse proof (systematics can share axes)

This probe asks: **can neural models trained on multiverse district dynamics find
the observatory’s preferred sky axis without being handed it?**  
That is the interaction half of “prove + interact.” Observational proof still needs
a new Gate 1–4 claim after P1.

---

## Protocol

| Item | Value |
|------|-------|
| Maps | Cached `wmap_k_band` (primary); optional `planck_smica_cmb` |
| Primary arms | `open_uniform`, `open_neural` (no hard feedback) |
| Telemetry | `physics_uniform`, `physics_neural` (feedback on) |
| Steps / nside | default 4 / 32 |
| Win | `open_uniform_final − open_neural_final ≥ 5°` |
| Fine-tune | `polomni neural finetune-real` merges physics-loop targets |
| Logging | `data/reports/m2_neural_real_sky_probe.json` |

```bash
bash scripts/build-corpus.sh 200
poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu
poetry run polomni neural train --epochs 100
poetry run polomni neural finetune-real --count 20 --epochs 80
poetry run polomni neural probe --map-product wmap_k_band --nside 32 --steps 4
```

**Current status (2026-08-24):** After `rewrite-history` on real WMAP preferred axis +
open-loop imprint pre-shift, **open_neural beats open_uniform by ~84°** (4.6° vs 89°).
Scar↔hierarchical ~4.4°. Physics loops with feedback ~4.5°. Computational interaction
win — not an observational multiverse detection.

---

## Path after a neural win

1. Repeat on Planck SMICA (calibration, not blind discovery)
2. Cross-check against bubble / cross-sky nulls (must stay honest)
3. Pre-register **P4** only if a *new* observable is unique under ΛCDM nulls
4. Methods paper: neural interaction appendix + falsified P1 as science done right
