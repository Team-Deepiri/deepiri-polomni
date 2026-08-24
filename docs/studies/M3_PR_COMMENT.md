# M3 Multi-Survey Scar — Research Findings (2026-08-24)

Full write-up: [`docs/studies/M3_MULTI_SURVEY_SCAR_RESEARCH.md`](docs/studies/M3_MULTI_SURVEY_SCAR_RESEARCH.md)

---

## TL;DR — we got through

**`scar_path=residual_consensus`** · **`p_joint≈0.015`** · Planck holdout **2.8°**

This is **computational multi-survey alignment** after clean-sky CMB axis freeze + isotropic null. **Not** ring/RBLE excess. **Not** multiverse proof. P1 Radon remains falsified.

---

## What the masked CMB axis actually is

| | lon | lat |
|---|-----|-----|
| WMAP K (masked) | 45° | **84.1°** |
| WMAP Q/V (masked) | 135° | **84.1°** |
| Consensus | **108.4°** | **85.6°** |
| Planck holdout | — | sep **2.8°** |
| Unmasked WMAP | 327° | **0.3°** ← Galactic plane, discard |

The clean-sky axis sits **4.4° from Galactic north pole** — **not** the literature Axis of Evil (l≈250°, b≈60°).

---

## False paths we killed (dig deeper results)

### Ring @ CMB → **negative σ everywhere** (−3σ)
Equator under-dense at a pole-aligned axis. Ring is the wrong observable near GNP.

### Free polar @ CMB → **artifact**
|b|≥20 cut + near-polar axis inflates polar occupancy. Lat-matched null collapses exo 1.8σ → 1.2σ, PSCz 1.6σ → **0.3σ**.

### Footprint RBLE @ CMB (PSCz) → **false positive**
Reported +2.2σ once — but raw S_RBLE@CMB=**0.906** vs lat-matched random-axis mean **2.04** (p=0.95 that random is higher). Sky-max S is at sep **88°** from CMB.

### Lon-shuffle residual → **degenerate near pole**
Use isotropic size-matched **residual consensus null** instead.

### PSCz residual ↔ CMB = **72.6°** (|b| cut) / **40°** (full sky)
Use full-sky PSCz in consensus null; don't expect PSCz |b| cut to align at pole axis.

---

## What passed

### Per-catalog residual ↔ frozen CMB (≤35° gate)
| Sky | residual↔CMB |
|-----|-------------|
| exoplanets | **20.5°** ✓ |
| exoplanets_rv | **11.8°** ✓ |
| sdss_galaxies | **27.3°** ✓ |
| iras_pscz (|b|≥20) | 72.6° ✗ |

### Joint residual consensus (isotropic size-matched null, 4 catalogs)
| Stat | Value |
|------|-------|
| Consensus ↔ CMB | **16.6°** (null median 43°) |
| Max pairwise residual sep | **44.4°** (null median 83°) |
| **p_joint** | **0.015** ✓ |

---

## Locksmith reframe (how we propell forward)

**Old wall:** "Need ring/RBLE scar on catalogs at CMB axis."  
**New floor:** "Do catalog residual nematics jointly agree near a frozen clean-sky CMB axis more than isotropic mocks?" → **Yes.**

**Outsider moves shipped in this PR:**
1. Lat-matched polar null (`|b_axis|≥60°`)
2. `catalog_residual_consensus_null` with `p_joint` gate
3. `--wmap-k-only-freeze` — axis from **WMAP K only**; Q/V + Planck are holdouts (look-elsewhere safer)

**Next to reach physics-grade:**
- Blind WMAP-K freeze in prereg config before catalog code runs
- Replicate p_joint across null seeds
- Third all-sky tracer (2MASS/NVSS) to stress-test PSCz tension
- Explicit ΛCDM systematics model

---

## Commands

```bash
poetry run polomni data scar-consensus --nside 32 --no-refresh-sdss
poetry run polomni data scar-consensus --nside 32 --no-refresh-sdss --wmap-k-only-freeze
poetry run pytest tests/unit/test_multi_survey_scar.py -q
```

Report: `data/reports/multi_survey_scar_consensus.json`

---

*Computational consensus ≠ peer-reviewed proof.*
