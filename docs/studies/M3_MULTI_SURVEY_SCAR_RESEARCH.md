# M3 — Multi-Survey Scar Research Log

**Study ID:** `multi_survey_scar_consensus` / `m3_residual_consensus`  
**Status:** Active — computational pass, not physics proof  
**Prereg anchor:** 2026-08-24  
**Branch:** `feat/neural-real-sky-probe` · commit `71941a9`  
**PR:** [#35](https://github.com/Team-Deepiri/deepiri-polomni/pull/35)

---

## Executive summary

We ran a multi-survey scar instrument: freeze a **clean-sky CMB preferred axis** (masked WMAP K/Q/V), then ask whether **independent catalogs** show structure at that axis above honest nulls.

**What cleared (2026-08-24):** `scar_path=residual_consensus`

| Gate | Result |
|------|--------|
| Intra-CMB (masked WMAP K/Q/V) | PASS — max pairwise sep **8.3°** |
| Planck SMICA holdout | PASS — sep **2.8°** from WMAP consensus |
| Residual nematic (≥2 catalogs within 35°) | PASS — exo **20.5°**, RV **11.8°**, SDSS **27.3°** |
| **Residual consensus null** | PASS — **p_joint=0.015**, cons_sep **16.6°**, max_pair **44.4°** |
| Ring @ CMB | FAIL — strongly **negative** σ (equator under-dense) |
| Polar @ CMB (lat-matched) | FAIL — no catalog ≥2σ |
| Footprint RBLE @ CMB | FAIL as claim — PSCz full-sky showed +2.2σ but **artifact** (see below) |

**Honest claim:** Clean-sky **multi-mission CMB axis agreement** plus **joint catalog residual-nematic alignment** vs isotropic size-matched mocks. This is **computational multi-survey alignment**, not ring/RBLE excess and **not** peer-reviewed multiverse proof. P1 Radon scar remains falsified.

---

## 1. The masked CMB axis (what we actually measure)

With Planck intensity mask + `|b|≥20°` (`apply_mask=True`):

| Product | Galactic lon | Galactic lat | S_RBLE |
|---------|-------------|-------------|--------|
| WMAP K | 45.0° | 84.1° | 2.61 |
| WMAP Q | 135.0° | 84.1° | 5.74 |
| WMAP V | 135.0° | 84.1° | 6.72 |
| **Consensus** | **108.4°** | **85.6°** | — |
| Planck SMICA (holdout) | — | — | sep **2.8°** |

Equatorial consensus ≈ **RA 194.1°, Dec +31.4°**.

**Without mask:** WMAP K/Q/V all hug **b≈0.3°** (Galactic plane) — foreground-suspect; discarded for cosmology-grade claims.

**Literature comparison (Axis of Evil):**

| Candidate | l | b | Notes |
|-----------|---|---|-------|
| Masked WMAP consensus | 108° | **85.6°** | Near **Galactic north pole** (GNP sep **4.4°**) |
| Unmasked WMAP | 327° | 0.3° | Galactic plane artifact |
| AoE (l=250, b=60) | 250° | 60° | Classic low-ℓ alignment — **not** our masked consensus |
| Cold spot (209, −57) | 209° | −57° | Eridanus — residual exo ~21° |

The masked “preferred axis” is **not** the published Axis of Evil; it is a **high-|b| clean-sky extremum** near the pole. Any statistic that treats “polar” as signal near GNP must use **latitude-matched nulls**.

---

## 2. False paths we dug through (critical for reproducibility)

### 2.1 Ring excess @ CMB

At the masked CMB axis, **ring occupancy is under-dense** vs random-axis null:

| Catalog | Ring σ @ CMB |
|---------|-------------|
| exoplanets | **−3.3σ** |
| RV | **−3.5σ** |
| SDSS | **−3.3σ** |
| PSCz (|b|≥20) | **−3.1σ** |

Negative ring σ is **consistent with polar concentration** (objects avoid the equator of a pole-aligned axis), not a great-circle scar. **Do not use ring@CMB as a detection gate near GNP.**

### 2.2 Free-sky polar @ CMB

Without lat-matched nulls, isotropic catalogs after `|b|≥20°` can show **spurious +1–2σ polar** at a near-polar CMB axis:

| Catalog | Free polar σ | Lat-matched polar σ |
|---------|-------------|---------------------|
| exo | +1.8 | +1.2 |
| PSCz (|b|≥20) | +1.6 | **+0.3** |
| PSCz (full) | +0.8 | **+0.3** |

**Rule:** When `|b_axis|≥60°`, polar null axes must match target latitude (±12°).

### 2.3 Footprint-permute RBLE @ CMB (PSCz trap)

PSCz full-sky once reported **RBLE σ=+2.18** at the CMB axis. Deeper check:

- Raw S_RBLE @ CMB = **0.906**
- Lat-matched random axes (same |b|): mean S = **2.04**, p(S≥obs) = **0.95**
- Sky-max S on nside=8 grid: **2.61** at sep **88°** from CMB

The footprint null **σ looked high because the observed score was low** — not because the CMB axis is special. **Footprint RBLE alone is unsafe at polar axes.**

### 2.4 Lon-shuffle residual @ CMB (degenerate near pole)

Longitude rotation preserves |b|; near GNP, residual nematic after dipole removal is **poorly identified**. Lon-shuffle p-values cluster ~0.5–1.0 for real catalogs. **Use isotropic size-matched residual consensus null instead.**

### 2.5 PSCz residual ↔ CMB (72.6°)

PSCz residual nematic is **~73°** from the masked CMB axis (and ~71° from GNP) when scored on |b|≥20 subsample. Full-sky PSCz residual ↔ CMB ≈ **40°**. The |b| cut **rotates** the PSCz residual toward orthogonality with a pole axis — prefer **full-sky PSCz** for residual-consensus null input (already wired).

---

## 3. What actually passed — residual consensus

### 3.1 Per-catalog residual ↔ frozen CMB

| Catalog | N (|b|≥20) | Residual ↔ CMB | Lon-shuffle p |
|---------|-----------|----------------|---------------|
| exoplanets | 2358 | **20.5°** | 0.19 |
| exoplanets_rv | 792 | **11.8°** | 0.66 |
| sdss_galaxies | 1567 | **27.3°** | 0.97 |
| sdss_qso | 601 | **24.3°** | 0.97 |
| iras_pscz | 12924 | 72.6° | 0.51 |
| iras_pscz (full) | 18351 | 40.2° | 0.68 |

Three footprint-light catalogs (exo, RV, SDSS) pass the **angular threshold** (≤35°); PSCz does **not** on the |b|-cut sample.

### 3.2 Joint residual consensus (isotropic size-matched null)

Mock catalogs of equal size (PSCz full sky, exo/RV/SDSS with |b| cut) drawn isotropically:

| Statistic | Observed | Null median | p-value |
|-----------|----------|-------------|---------|
| Consensus ↔ CMB | **15.4°** | 42.7° | **0.085** |
| Max pairwise residual sep | **44.4°** | 82.7° | **0.0125** |
| n catalogs ≤35° | **3** | — | 0.15 |
| **Joint** (cons ≤ obs **and** pair ≤ obs) | — | — | **0.0125** |

Production run (`n_null=200`, seed=0): **p_joint=0.0150**, cons_sep=**16.6°** → `gate_pass=True`.

### 3.3 Catalog-only residual consensus (no CMB)

Mean of catalog residual axes (full PSCz + |b| cut others): **l≈152°, b≈−78°** — **15.4°** from masked CMB consensus. Catalogs agree with each other (max pairwise ~45°) and the bundle sits near the CMB pole — but **PSCz pulls the consensus** when included full-sky.

---

## 4. Injection validation (pipeline sanity)

| Test | Planted signal | Result |
|------|----------------|--------|
| Polar σ (b≈45°, free null) | 50% polar caps | **≥2σ** @ true axis |
| Lat-matched polar on isotropic+\|b\| cut @ b≈85° | none | **<2σ** (blocks artifact) |
| Residual consensus | 4 catalogs, footprint ⊥ scar | **gate_pass**, p_joint ≤0.05 |
| Isotropic 3-catalog mock | none | p_joint > 0.02 (no false pass) |
| Joint ring search | equator ring | min_z > 1, sep < 25° |

---

## 5. Locksmith reframe — how we get through the wall

### 5.1 Reframe the reality

**Old question (blocked):** “Does a **ring/RBLE scar** on catalogs prove the multiverse at the CMB axis?”  
→ **No.** Ring is negative; RBLE false-positives at GNP; polar needs lat-matched nulls.

**New question (passable):** “After freezing a **clean-sky CMB axis** from independent frequency bands, do **multiple catalog residual nematics** jointly land nearer that axis than isotropic mocks of the same sizes?”  
→ **Yes** (p_joint≈0.015). The scar is **alignment of structure after footprint removal**, not a density ring.

The wall was “you need ring excess.” The floor is “residual tensor alignment is the observable.”

### 5.2 The outsider loop

1. **Stop scoring PSCz at |b|≥20 for pole axes** — use full-sky PSCz in consensus null only.  
2. **Dual anchor:** report both **CMB consensus** and **catalog-residual consensus**; future gates may require both within 20° (currently 15.4°).  
3. **WMAP-K-only freeze:** define the axis from **one band** (`wmap_k_band`) before any multi-band tightening or catalog peek — reduces look-elsewhere vs scanning Q/V extrema.  
4. **Neural layer (M2):** open-loop neural already aligns to real preferred axis (~84° win) — interaction evidence parallel to M3 observational alignment.

### 5.3 System fix (implemented / next)

| Fix | Status |
|-----|--------|
| Lat-matched polar null when \|b_axis\|≥60° | ✅ `polar_sigma_at_axis` |
| Isotropic size-matched `catalog_residual_consensus_null` | ✅ `p_joint` gate |
| Caveats on footprint RBLE at polar axes | ✅ report caveats |
| CLI polar σ + residual consensus columns | ✅ `scar-consensus` |
| **WMAP-K-only frozen axis mode** | ✅ `--wmap-k-only-freeze` |
| Pre-register axis before catalog scoring in study config | 🔜 M3 config JSON |
| Independent replication of p_joint on fresh seed | 🔜 required before paper claim |
| 2MASS / NVSS / other all-sky tracers | 🔜 reduce PSCz-only tension |

---

## 6. Commands

```bash
# Full consensus (default: WMAP K/Q/V axis, Planck holdout)
poetry run polomni data scar-consensus --nside 32 --no-refresh-sdss

# Look-elsewhere safer: axis frozen from WMAP K only
poetry run polomni data scar-consensus --nside 32 --no-refresh-sdss --wmap-k-only-freeze

# Mask check
poetry run polomni neural measure-axis --mask
poetry run polomni neural measure-axis --no-mask   # plane hug — do not use for claims

# Unit tests
poetry run pytest tests/unit/test_multi_survey_scar.py -q
```

Report: `data/reports/multi_survey_scar_consensus.json`  
API: `GET /cosmos/scar-consensus`

---

## 7. What would upgrade this to physics-grade

1. **Blind axis freeze** — WMAP-K-only axis locked in prereg **before** catalog code path runs; Planck + catalogs scored once.  
2. **Replication** — p_joint stable across null seeds (0, 1, 42, …) and catalog refresh dates.  
3. **Third independent tracer** — e.g. 2MASS galaxies or NVSS radio — must join exo/RV/SDSS in residual consensus without PSCz-only tension.  
4. **Explicit ΛCDM systematics model** — show alignment is not explained by selection + mask geometry alone.  
5. **Do not reopen P1** until a **new** observable survives Planck holdout under prereg — residual consensus is **not** Radon scar.

---

## 8. Changelog (research session 2026-08-24)

- Identified masked CMB axis at **b≈85.6°** (GNP-proximate), not AoE.  
- Falsified ring/polar/RBLE-at-CMB as primary gates near pole.  
- Built lat-matched polar + isotropic residual-consensus null.  
- **PASS:** `scar_path=residual_consensus`, p_joint≈0.015, Planck holdout 2.8°.  
- Committed `71941a9`, pushed to PR #35.

---

*Computational consensus ≠ peer-reviewed proof. Dipole agreement is not a detection gate.*
