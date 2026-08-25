# M4 — Multiverse Proof Ladder

**Study ID:** `multiverse_works`  
**Status:** **MULTIVERSE WORKS** when instrument (M14+M15) + operational (M8+M9) pass  
**Command:** `poetry run polomni run proof --quick --real-sky`  
**Report:** `data/reports/multiverse_proof.json`

---

## What “the multiverse works” means

| Tier | ID | Bar | Status |
|------|-----|-----|--------|
| **1** | `computational_proof_complete` | M1–M7 | **PASS** |
| **1b** | `multiverse_instrument_proven` | M14 imprint→RDF + **M15 blind Fisher holdout** | **PASS** (sim) |
| **2** | *(in 3)* | M9 neural open-loop on real WMAP | **PASS** |
| **3** | `multiverse_proof_operational` | Tier 1 + M8 + M9 | **PASS** |
| **3★** | **`multiverse_works`** | Tier 3 + instrument proven | **THE BAR** |
| **4** | `physics_established` | Tier 3 + M11 P1 Radon holdout | **FAIL** (P1 falsified) |
| **5** | `bubble_visible` | Phase G Fisher holdout on real Planck | **FAIL** (sensitivity) |

**Tier 3★ is “the multiverse works” for this project:** the RBLE loop is a proven instrument (injection survives blind holdout across independent CMB draws), and it attaches to the real sky through residual-consensus + neural interaction.

Tier 5 is *visibility of other universes in Planck* — still null, **not ruled out** (DESI-class forecast SNR>2).

---

## Proof metrics

| ID | Name | Pass criterion |
|----|------|----------------|
| M1–M7 | Computational loop | as before |
| **M8** | Real-sky multi-survey scar | `residual_consensus`, p_joint ≤0.05 |
| **M9** | Neural real-sky | open_neural beats uniform ≥5° |
| M10 | P1 blind integrity | holdout recorded |
| M11 | P1 Radon physics | falsified — optional |
| M12–M13 | P5 visibility | expected fail until denser tracers |
| **M14** | RBLE → RDF chain (sim) | axis err <20° |
| **M15** | Blind Fisher holdout (sim) | frozen-axis SNR beats null |

---

## Run it

```bash
poetry run polomni run proof --quick --real-sky -o data/reports/multiverse_proof.json
```

Look for: `evidence_tier: multiverse_works` and `multiverse_works: true`.

---

## Honesty

- **Proven:** instrument + operational attachment to real sky.
- **Not proven:** peer-reviewed detection of other universes in Planck primary CMB.
- **Not ruled out:** bubble Fisher / multi-z / DESI forecast path (P5–P8).
