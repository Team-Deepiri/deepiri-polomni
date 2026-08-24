# Registered Studies

Pre-registered, blind-capable observatory analyses for establishing RBLE as physics.

| Study | Document | Config | Status |
|-------|----------|--------|--------|
| **P1** CMB Radon scar | [P1_CMB_RADON_SCAR_PREREG.md](./P1_CMB_RADON_SCAR_PREREG.md) | `data/studies/p1_holdout/study_config.json` | Registered — holdout pending |
| **M2** Neural real-sky probe | [M2_NEURAL_REAL_SKY_PROBE_PREREG.md](./M2_NEURAL_REAL_SKY_PROBE_PREREG.md) | CLI / `data/reports/m2_*` | Active — open-loop neural win |
| **M3** Multi-survey scar | [M3_MULTI_SURVEY_SCAR_RESEARCH.md](./M3_MULTI_SURVEY_SCAR_RESEARCH.md) | `polomni data scar-consensus` | Active — `residual_consensus` pass |
| **M4** Multiverse proof ladder | [M4_MULTIVERSE_PROOF_LADDER.md](./M4_MULTIVERSE_PROOF_LADDER.md) | `polomni run proof --real-sky` | **Operational proof achieved** |
| **P5** Other universes visible (SOTA) | [P5_OTHER_UNIVERSES_VISIBLE_SOTA.md](./P5_OTHER_UNIVERSES_VISIBLE_SOTA.md) | `polomni data rdf-tomography` | **Phase A proxy implemented; no visibility detection** |

**Run calibration:** `polomni study run p1 --calibration`  
**Run blind holdout:** `polomni study run p1 --blind`  
**Replicate:** [REPLICATION_P1.md](../guides/REPLICATION_P1.md)

See [PHYSICS_ESTABLISHMENT.md](../PHYSICS_ESTABLISHMENT.md) for gate sequence and success metrics.
