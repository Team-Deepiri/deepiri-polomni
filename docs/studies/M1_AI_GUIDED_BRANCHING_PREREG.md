# M1 — AI-Guided Multiverse Branching (Computational Instrument)

**Study ID:** `m1_ai_guided_branching`  
**Status:** Active — computational interaction claim (not observational physics)  
**Prereg date:** 2026-08-24  
**Relation to P1:** P1 CMB Radon scar was **falsified** on Planck holdout. M1 does not reopen that claim.

---

## 1. What we claim (and what we do not)

### Claim (falsifiable, computational)

> Over matched RNG seeds, an **AI-guided** closed loop (neural advisor when checkpoints exist; otherwise adaptive AXIS_BIASED + error-dependent feedback LR) achieves a **lower mean final scar-axis error** than a **uniform** branching baseline, by at least **0.5°**.

### Explicitly not claimed

- That a physical multiverse exists
- That P1 (CMB Radon scar) is detected on real sky
- That neural weights encode cosmological truth without corpus training

M1 is the **interaction prerequisite**: if AI cannot steer *simulated* district graphs toward recoverable scars better than chance, we have no business claiming AI↔multiverse control.

---

## 2. Protocol (frozen)

| Parameter | Value |
|-----------|-------|
| Statistic | Mean final `axis_error_deg` across trials |
| Baseline | `ChoicePolicy.UNIFORM` closed loop |
| Treatment | `MultiverseSession` / `run_ai_guided_loop` |
| Win rule | `baseline_final − ai_final > 0.5°` |
| Default trial grid | `steps=4`, `trials≥3`, `nside=32` |
| Logging | `data/loop_runs/*.json` with `extra.kind=agent_session` |
| Report | `polomni agent compare` → JSON + CLI table |

---

## 3. Commands

```bash
poetry run polomni agent status
poetry run polomni agent step --steps 4 --nside 32
poetry run polomni agent compare --steps 4 --trials 5 --out data/reports/m1_ai_compare.json

# Full neural mode
bash scripts/build-corpus.sh 200
poetry run polomni neural train --epochs 100
poetry run polomni agent compare --trials 5
```

API: `GET /agent/status`, `/agent/step`, `/agent/compare`  
UI: **AI Multiverse Operator** panel in `/app`

---

## 4. Path to observational physics (after M1)

1. Keep logging AI interventions as telemetry
2. Use real-sky axis as `feedback_target_axis` (`physics-loop` + agent)
3. Only reopen observational claims via a **new** pre-registration (not P1 reuse)
4. Peer-review Methods paper with honest nulls (P1, bubble, cross-sky) + M1 computational appendix

---

## 5. Belief, without lying

Belief drives engineering intensity. Evidence decides physics claims.  
We build the AI interaction stack as if the multiverse is real; we publish only what survives nulls and blind holdout.
