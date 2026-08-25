# Registered Studies

Pre-registered, blind-capable observatory analyses for establishing RBLE as physics.

| Study | Document | Config | Status |
|-------|----------|--------|--------|
| **P1** CMB Radon scar | [P1_CMB_RADON_SCAR_PREREG.md](./P1_CMB_RADON_SCAR_PREREG.md) | `data/studies/p1_holdout/study_config.json` | Registered — holdout pending |
| **M2** Neural real-sky probe | [M2_NEURAL_REAL_SKY_PROBE_PREREG.md](./M2_NEURAL_REAL_SKY_PROBE_PREREG.md) | CLI / `data/reports/m2_*` | Active — open-loop neural win |
| **M3** Multi-survey scar | [M3_MULTI_SURVEY_SCAR_RESEARCH.md](./M3_MULTI_SURVEY_SCAR_RESEARCH.md) | `polomni data scar-consensus` | Active — `residual_consensus` pass |
| **M4** Multiverse proof ladder | [M4_MULTIVERSE_PROOF_LADDER.md](./M4_MULTIVERSE_PROOF_LADDER.md) | `polomni run proof --real-sky` | **Operational proof achieved** |
| **P5** Other universes visible (SOTA) | [P5_OTHER_UNIVERSES_VISIBLE_SOTA.md](./P5_OTHER_UNIVERSES_VISIBLE_SOTA.md) | `polomni data rdf-tomography` | **Phase G blind holdout — not ruled out** |
| **P6** Fisher bubble invariant | [P6_FISHER_BUBBLE_INVARIANT.md](./P6_FISHER_BUBBLE_INVARIANT.md) | `multiverse_fisher_scan.py` | Phase E complete |
| **P7** Multi-z tomography | [P7_MULTI_Z_TOMOGRAPHY.md](./P7_MULTI_Z_TOMOGRAPHY.md) | `multi_z_tomography.py` | Phase F complete |
| **P8** Blind Fisher holdout | [P8_BLIND_FISHER_HOLDOUT.md](./P8_BLIND_FISHER_HOLDOUT.md) | `blind_fisher_holdout.py` | Phase G complete |
| **P9** Dense LRG Fisher | [P9_DENSE_LRG_FISHER.md](./P9_DENSE_LRG_FISHER.md) | `polomni data dense-lrg-fisher` | Phase H |
| **P10** Planck visibility path | [P10_PLANCK_VISIBILITY_PATH.md](./P10_PLANCK_VISIBILITY_PATH.md) | resources + goals | Active |
| **P11** Hammer visibility | [P11_HAMMER_VISIBILITY.md](./P11_HAMMER_VISIBILITY.md) | `polomni data hammer-fisher` | **Hammering** |

**Run calibration:** `polomni study run p1 --calibration`  
**Run blind holdout:** `polomni study run p1 --blind`  
**Replicate:** [REPLICATION_P1.md](../guides/REPLICATION_P1.md)

See [PHYSICS_ESTABLISHMENT.md](../PHYSICS_ESTABLISHMENT.md) for gate sequence and success metrics.
