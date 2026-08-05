# Changelog

All notable changes to **deepiri-polomni** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Bubble-collision search** — the one multiverse signature with a concrete, falsifiable observable: in eternal inflation a bubble colliding with ours leaves a **circular temperature edge** in the CMB. New instrument (`polomni data bubble`, `GET /cosmos/bubble-search`, BubbleSearchCard in the World Atlas panel) scans a real CMB map (Planck SMICA) for such edges: circle-edge statistic (⟨T⟩ outside − inside), C_ℓ- and mask-matched Gaussian null with look-elsewhere correction, an **injection gate** that recovers planted collision steps exactly (same center, same radius), and a radial-profile step check so smooth gradients can't masquerade as bubbles. **Current real-data result: no significant circular edge (strongest 35.9 µK vs null median 34.6 µK, p≈0.35)** — consistent with the published null (Feeney et al. 2011). Includes the Galactic-mask frame fix (Planck maps ship in Galactic coordinates) and the mask-hugging guard that excludes circles straddling the cut. Theory: `docs/theory/WORLD_ATLAS.md`; tests: `tests/unit/test_bubble_collisions.py`, `tests/api/test_cosmos.py`.
- **Rank-1 harmonic-axis search** — a second, scale-free collision statistic added to the bubble instrument. By the spherical-harmonic **addition theorem**, a collision about axis n̂_c has `a_lm = C_l·Y_lm(n̂_c)` at **every** l — the map is axisymmetric about the collision axis, so its **m=0 power fraction** at the true axis is 1 at each multipole (vs the isotropic `1/(2l+1)`). The search rotates the map per candidate axis and sums the m=0-fraction excess; the CMB's own low-multipole alignment ("axis of evil") is absorbed into the C_ℓ-matched null instead of being reported as a detection. Injection gate: planted axis recovered to ~3° and beats the null at ≥ ~300 µK; **real Planck result: no axisymmetric structure above the null** (honest null, look-elsewhere corrected). Includes the healpy alm-layout fix (column-major m-blocks, not `l(l+1)/2+m`), the corrected Euler rotation convention `[φ, −θ, 0]`, and correct monopole+dipole removal (indices by `l,m`). New: `harmonic_axis_search`, `_rank1_score`, `_prepare_map` in `sources/bubble_collisions.py`; `harmonic_axis` section on `GET /cosmos/bubble-search` (`n_null_rank1`), `--n-null-rank1` on `polomni data bubble`, rank-1 block in BubbleSearchCard. Tests: `tests/unit/test_bubble_collisions.py`, `tests/api/test_cosmos.py`. Theory: `docs/theory/WORLD_ATLAS.md`.
- **Cross-sky axis test** — the sharpest falsifier of a *world* scar: every independent sky must point at the same preferred axis, or there is no axis. Compares the world dipole across every cached independent sky. **Current result: exoplanets ↔ SDSS galaxies disagree by 71.9°** — no common axis, each dipole points at its own survey footprint (exoplanets → Kepler field 4.8°, SDSS → northern galactic cap). GWTC `network_axis` is detector geometry (5 unique directions / 100 events), now rejected with a guard instead of shipped as a sky direction. New: `cross_sky_report`, `sky_dipole_report`, `sky_samples`, `load_gw_vectors` guard in `sources/cross_sky.py`; `GET /cosmos/cross-sky`; `polomni data cross-sky`; cross-sky card in the World Atlas panel. Theory: `docs/theory/WORLD_ATLAS.md`.
- **World dipole robustness** — the cosmic-rest-frame dipole test now ships two adversarial robustness checks: **per-host bootstrap** (resamples the 4,747 *systems*, not the 6,333 planets, respecting that planets in one system share a sky position — dipole 0.407, still 6.4° from Kepler) and the **Kepler-excision scan** (dipole magnitude vs worlds excised within 5/8/12/20° of the Kepler field — collapses 0.422 → 0.075, i.e. toward the isotropic expectation, once the footprint is removed). New: `per_host` on `dipole_bootstrap`, `kepler_excision_scan` in `sources/exoplanets.py`; `bootstrap_per_host` + `kepler_excision` on `GET /cosmos/worlds`; excision table in `polomni data worlds` and the World Atlas panel. Theory: `docs/theory/WORLD_ATLAS.md`.
- **World dipole + power spectrum** — the World Atlas now ships the **cosmic-rest-frame dipole test** (world dipole vs CMB apex / ecliptic pole / Galactic pole / Kepler field, with a 68% bootstrap cone per method) and the **world-sky angular power spectrum C_ℓ** (a novel observable for the confirmed-planet sky) with a uniform-within-footprint null. Current result: the only significant multipole is ℓ=1, which is the Kepler-field dipole (~6.5σ) — no world scar survives beyond the survey footprint. New: `world_dipole`, `dipole_bootstrap`, `reference_alignment_table`, `method_dipole_scan`, `world_power_spectrum`, `spectrum_null_percentiles` in `sources/exoplanets.py`; `dipole` + `spectrum` fields on `GET /cosmos/worlds`; `--null` on `polomni data worlds`; dipole marker + C_ℓ chart in the World Atlas panel. Theory: `docs/theory/WORLD_ATLAS.md`.
- **World Atlas** — maps the real sky positions of every confirmed exoplanet (NASA Exoplanet Archive, `nasa_exoplanet_ps`) to a HEALPix density map and runs the RBLE geodesic-Radon scar scan over the distribution of worlds. Includes a **footprint-matched null** (counts reshuffled within the survey mask) and a **per-method axis audit** referenced to the Galactic pole, so a scar claim is not a Kepler-field or disk-plane artifact. `polomni data worlds`, `GET /cosmos/worlds`, and a MapLibre **World Atlas** frontend panel. Theory + invariants: `docs/theory/WORLD_ATLAS.md`.
- **Exoplanet source adapter** — `nasa_exoplanet_ps` CSV product (`csv` kind) in the data catalog; parser, RA/Dec→HEALPix density maps, alignment (nematic) tensor with the Tr(Q)≡1 invariant, footprint-permuted nulls (`src/polomni/observatory/pipeline/sources/exoplanets.py`).
- **Math proof engine** — `polomni.math` provers for VP + Eq1–8 + falsification P1–P3; `polomni math prove` CLI and `/math/*` API.
- **Proof notebooks** — `experiments/09`–`13` variational principle, falsification trinity, integrated loop, Kähler Eq8, real-data bridge.
- **Viz API** — `/viz/*` JSON serializers for multiverse visualizations (`src/polomni/viz/multiverse/`).
- **React frontend** — Vite app in `frontend/` with 7 scientist panels; served at `/app` after `npm run build`.
- **Hierarchical sky search** — coarse-to-fine RBLE axis search (`--hierarchical` on `polomni scan`).
- **Report CLI** — `polomni report list|show|latest|compare` for detection JSON management.
- **Data analytics** — `polomni data plot power|gw` and `polomni data correlate` for GW–RBLE correlation.
- **API metrics & dashboard** — `GET /metrics`, `GET /dashboard` with inline lab UI.
- **Report compare API** — `POST /observatory/compare`.
- **Batch simulation** — `polomni simulate batch` across multiple RNG seeds.
- **Makefile** — `make test`, `verify`, `docker-up`, `serve`, `smoke`.
- **Docker watch service** — `polomni-watch` profile for continuous GWOSC polling.

## [0.1.0] - 2026-06-28

### Added

- **Real data pipeline** — `polomni data` commands to fetch Planck/WMAP/GWOSC products, cache under `data/cache/`, run full RBLE observatory pipeline, and watch GWOSC with optional re-scan (`src/polomni/observatory/pipeline/`).
- **REST API** — FastAPI lab surface via `polomni serve`: health, data catalog/status/fetch, observatory scan/pipeline/reports, and SSE GW poll stream (`src/polomni/api/`).
- **Visualization CLI** — `polomni viz sky|district|stream` for Mollweide sky maps, district graphs, and Radon vacuum stream plots (`src/polomni/viz/`).
- **Lab integration workflow** — `polomni run workflow` and `polomni run benchmark` orchestrate ingest → district simulation → RBLE pipeline (`src/polomni/integration/`).
- **Environment info** — `polomni info` prints version, optional deps, and cache summary.
- **Documentation** — Real-time data guide, API reference, data pipeline architecture, and notebooks `experiments/07_real_data_pipeline.ipynb`, `experiments/08_api_workflow.ipynb`.
- **CI** — `data-pipeline-smoke.yml` workflow for pipeline CLI smoke checks on `main`/`dev`.

### Changed

- `polomni serve` now mounts the full REST API via `create_app()` instead of health-only stubs.
- `polomni scan --real` loads cached FITS maps from the data pipeline catalog.
