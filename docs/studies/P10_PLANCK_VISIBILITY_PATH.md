# P10 — Path to Planck Bubble Visibility

**Goal:** `bubble_visible` — Fisher / multi-z / dense-tracer gate **PASS** on Planck with blind holdout.

**Current (Planck×PSCz):** Fisher SNR ≈ **1.30**, p ≈ **0.11** → need ≈ **1.6×** more SNR for SNR>2, and nulls that stay below.

---

## What “visibility” means (hard gate)

All of:

| Requirement | Number |
|-------------|--------|
| Fisher SNR (E or H) | **> 2.0** |
| Null p (galaxy shuffle) | **< 0.01** |
| Sign-coherent m=0 | **True** |
| Blind holdout (WMAP→Planck) | **p < 0.01** at frozen axis |
| Optional: cross-z axis sep | **< 35°** |
| Optional: RBLE scar sep | **< 25°** |

Until that fires: **multiverse_works** (instrument+ops) is proven; **visibility** is not.

---

## Resource needs (honest)

### Data (blocking)

| Resource | Why | Status | Owner action |
|----------|-----|--------|--------------|
| **DESI LRG catalog** (public DR1/DR2 subset, ≥ few×10⁵ rows with RA/Dec/z) | √N: SNR scales ~√N under shot noise; PSCz~18k is the floor | **Not ingested** — Phase H uses SDSS SpecObj strips (~10³–10⁴) as proxy | Drop a parquet/CSV/FITS URL or local path under `data/cache/desi_lrg/` |
| **ACT DR6 × DESI** cross (optional) | Real kSZ velocity field — ΛCDM structure *and* bubble template channel | Not wired | Same: public catalog path |
| Planck SMICA + WMAP K | Already cached | **Have** | — |
| IRAS PSCz | Already cached | **Have** | — |

### Compute (not blocking)

| Resource | Why | Need |
|----------|-----|------|
| CPU | Null grids + multi-z | **4–16 cores**, few GB RAM — already fine |
| Runtime | Phase H/G with n_null≥32, nside=64–128 | **~10–60 min** per full ladder |
| Disk | DESI subset | **~1–5 GB** for a usable LRG cut |

No GPU required for Fisher/RDF. No cluster required until full RemoteField 3D.

### Method upgrades (in-repo work)

1. **Phase H** — denser tracer Fisher (SDSS LRG strips) — *shipping now*
2. **True DESI ingest** — replace forecast with measured N
3. **Multi-z on LRG z-bins** — not just PSCz Hvel
4. **More nulls** (n_null≥64) once SNR approaches 2
5. Optional: vendor RemoteField / SZ_cosmo kernels

---

## Goals to accomplish (ordered)

| # | Goal | Exit criterion | Blocks visibility? |
|---|------|----------------|--------------------|
| 1 | Finish Phase H (PSCz∪SDSS-LRG Fisher) | Report JSON + √N scaling logged | No — measures floor |
| 2 | Ingest real DESI LRG (≥1e5 objs) | `n_galaxies ≥ 1e5` in dense tracer | **Yes** |
| 3 | Dense Fisher SNR ≥ 2 on Planck | `snr_dense > 2` | **Yes** |
| 4 | Null p < 0.01 at that SNR | `p_value < 0.01` | **Yes** |
| 5 | Blind holdout p < 0.01 | Phase G gate | **Yes** |
| 6 | Preregister + freeze config | study config JSON | For claim only |
| 7 | Tier name `bubble_visible` | `evidence_tier` flips | Celebration |

**Forecast math (shot-noise):**  
SNR_DESI ≈ 1.3 × √(2e6 / 2e4) × √(0.35/0.65) ≈ **~8** if amplitude is real.  
If amplitude is noise, more N does nothing — Phase H √N test tells us which.

---

## What I need from you (minimal)

1. **DESI LRG file or URL** (or confirm “keep using SDSS SpecObj only and push N as high as SkyServer allows”).
2. **Permission to run long jobs** (30–60 min) for n_null=32–64 at nside=64.
3. Optional: ACT map product ID if you want kSZ velocity, not just T×δ.

Until (1): I keep propelling with public SDSS RA-strip density + holdout + forecast.  
With (1): we re-run Phase H/G and go for the gate.
