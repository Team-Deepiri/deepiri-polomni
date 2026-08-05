# Changelog

All notable changes to **deepiri-polomni** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
