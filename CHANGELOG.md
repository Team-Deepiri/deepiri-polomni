# Changelog

All notable changes to **deepiri-polomni** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
