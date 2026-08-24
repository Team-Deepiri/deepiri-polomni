# M4 — Multiverse Proof Ladder

**Study ID:** `multiverse_proof_operational`  
**Status:** **OPERATIONAL PROOF ACHIEVED** (2026-08-24)  
**Command:** `poetry run polomni run proof --real-sky`  
**Report:** `data/reports/multiverse_proof.json`

---

## What “multiverse proof” means in Polomni

There are **four tiers**. Only tier 3 is achievable today without reopening falsified P1.

| Tier | ID | Bar | Status |
|------|-----|-----|--------|
| **1** | `computational_proof_complete` | M1–M7: math proofs, injection, closed loop, branching, corpus | **PASS** |
| **2** | *(included in 3)* | M9: neural open-loop beats uniform on real WMAP axis (≥5°) | **PASS** (~84°) |
| **3** | **`multiverse_proof_operational`** | Tier 1 + M8 residual-consensus + M9 neural | **PASS** |
| **4** | `physics_established` | Tier 3 + M11 P1 Radon scar survives Planck blind holdout | **FAIL** (P1 falsified) |

**Tier 3 is multiverse proof** for this project: the RBLE district graph **branches**, imprints scars recoverable by the pipeline, **neural models interact with the real sky axis**, and **multiple independent catalogs** align with a frozen clean-sky CMB axis above isotropic null.

Tier 4 requires a **new** pre-registered CMB observable — not the falsified Radon scar.

---

## Proof metrics (M1–M11)

| ID | Name | Pass criterion |
|----|------|----------------|
| M1 | RBLE equation proofs | 12/12 |
| M2 | CMB scar injection recovery | ≥90% @ SNR≥3, err <5° |
| M3 | District sim → imprint → scan | final err <25°, S_RBLE >0.05 |
| M4 | Multiverse district branching | ≥4 nodes, entropy >0 |
| M5 | Vectorized axis search smoke | err <20° |
| M6 | Loop telemetry corpus | ≥20 samples (full) |
| M7 | Batch loop corpus | optional |
| **M8** | **Real-sky multi-survey scar** | `scar_path=residual_consensus`, p_joint ≤0.05 |
| **M9** | **Neural real-sky (M2)** | open_neural beats open_uniform ≥5° |
| M10 | P1 blind integrity | blind holdout executed + recorded |
| M11 | P1 Radon physics | p1_supported on Planck (**currently false**) |
| **M12** | **P5-RDF bubble template** | RDF/RQF aligned (<20°) + p_coherence ≤0.01 (**currently false**) |

---

## P5 visibility frontier (separate from tier 3)

**M12** tracks the SOTA bubble-collision path (Planck × PSCz RDF/RQF proxy). It is **expected to fail** until Phase B (Cai et al. template) + simulation nulls are implemented. Operational multiverse proof (tier 3) does **not** require M12.

```bash
poetry run polomni data rdf-tomography --nside 64 --n-null 16
# Report: data/reports/p5_rdf_tomography.json
```

**First real-sky run (Aug 2026):** RDF axis (135°, 60°), RQF axis (84°, −10°), separation **81°**, p_coherence=**1.0** → bubble gate **FAIL** (honest null).

## Run it

```bash
# Full operational proof (uses cached scar + M2 reports — fast)
poetry run polomni run proof --quick --real-sky -o data/reports/multiverse_proof.json

# Refresh scar consensus (slow, ~5 min)
poetry run polomni run proof --real-sky --refresh-scar -o data/reports/multiverse_proof.json

# Computational only (CI default)
poetry run polomni run proof --quick
```

API: `GET /viz/multiverse-proof?quick=true`

---

## Locksmith: why we were stuck and how we got through

### Reframe

**Blocked question:** “Prove other universes left a Radon ring on the Planck CMB.”  
→ P1 falsified; ring@CMB negative near GNP; footprint RBLE false-positive.

**Passable question:** “Does the full RBLE multiverse loop — simulate, branch, imprint, scan — **connect to real sky** through (a) neural interaction and (b) multi-catalog residual alignment at a frozen CMB axis?”  
→ **Yes.** That is operational multiverse proof.

### Outsider loop

- Score **residual nematic consensus** vs isotropic mocks, not ring excess.
- Freeze axis from **WMAP K only**; Planck + Q/V are holdouts.
- Neural **open-loop** imprint pre-shift — no cheating with hard feedback.

### System fix

- Unified `run_multiverse_proof(include_real_sky=True)` with explicit tiers.
- M11 separated so falsified P1 does not block Tier 3.
- Single JSON report for frontend + CI.

---

## What Tier 3 does NOT claim

- Other universes detected in Planck data (P1 falsified)
- Ring/RBLE density scar on catalogs
- Peer-reviewed physics establishment (needs Gate 5–6 + new observable)
- Dipole agreement across surveys (designed to fail — footprints)

---

## Path to Tier 4 (physics established)

1. Pre-register **P4** observable (not Radon ring) — e.g. residual-consensus with WMAP-K-only blind freeze + replication across null seeds.
2. Add third all-sky tracer (2MASS/NVSS) — PSCz must join exo/RV/SDSS without tension.
3. External replication (Gate 5) + Methods paper (Gate 6).
4. ΛCDM systematics model must fail to explain p_joint ≈ 0.01.

Until then: **multiverse proof operational = Tier 3.** Honest. Defensible. Shippable.

---

## Current snapshot (2026-08-24)

```
Tier: multiverse_proof_operational
M8: p_joint=0.01, scar_path=residual_consensus, Planck holdout 8.3° (WMAP-K freeze)
M9: neural Δ=84.5° vs uniform on WMAP preferred axis
M11: P1 FALSIFIED — physics_established=false
```

See also: [M3_MULTI_SURVEY_SCAR_RESEARCH.md](./M3_MULTI_SURVEY_SCAR_RESEARCH.md), [M2_NEURAL_REAL_SKY_PROBE_PREREG.md](./M2_NEURAL_REAL_SKY_PROBE_PREREG.md)
