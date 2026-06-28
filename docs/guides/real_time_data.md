# Real-Time Data Pipeline

Guide to fetching live cosmology data, managing the local cache, running the RBLE observatory pipeline, and operating the GWOSC watch loop.

**Related:** [cmb_data_pipeline.md](./cmb_data_pipeline.md) · [../architecture/DATA_PIPELINE.md](../architecture/DATA_PIPELINE.md) · [api_reference.md](./api_reference.md)

---

## Overview

The real-time pipeline connects public NASA/ESA/GWOSC endpoints to the RBLE CMB scar detector:

```
NASA LAMBDA / IRSA Planck / GWOSC API
        ↓ fetch
   data/cache/  (manifest.json)
        ↓ ingest
   HEALPix map + cosmology params
        ↓ score
   RBLE signature + null ensemble
        ↓ report
   data/reports/*.json
```

Implementation: `src/polomni/observatory/pipeline/`

---

## Data Sources

| Product ID | Source | Tier | Size | Use |
|------------|--------|------|------|-----|
| `planck_cmb_tt_power` | IRSA Planck DR3 binned TT C_l | lite | ~KB | Landscape calibration, power spectrum plots |
| `planck_lcdm_baseline` | IRSA Planck ΛCDM theory C_l | lite | ~KB | Ω_Λ proxy / baseline comparison |
| `wmap_k_band` | NASA LAMBDA WMAP 9yr Ka-band FITS | standard | ~100 MB | Default real-sky RBLE scan target |
| `planck_smica_cmb` | IRSA Planck SMICA IQU 2048 | heavy | ~384 MB | High-resolution production scans |
| `planck_int_mask` | IRSA Planck intensity mask | standard | ~MB | Galactic/point-source masking |
| `gwtc_events` | GWOSC GWTC JSON API | real-time | ~KB | Gravitational-wave event catalog |

Catalog definition: `src/polomni/observatory/pipeline/catalog.py`

GWOSC endpoint (no API key required):

```
https://gwosc.org/api/v2/catalogs/GWTC/events?format=json
```

---

## CLI Commands

### List and inspect

```bash
poetry run polomni data list      # full catalog table
poetry run polomni data status    # cached vs missing per product
poetry run polomni info           # version, deps, cache summary
```

### Fetch

```bash
# Default: lite Planck products + GWTC refresh
poetry run polomni data fetch

# Lite only, skip GW polling
poetry run polomni data fetch --no-gw

# Add WMAP map for scanning (~100 MB)
poetry run polomni data fetch --wmap

# Specific products
poetry run polomni data fetch planck_cmb_tt_power planck_lcdm_baseline

# Force re-download (ignore cache freshness)
poetry run polomni data fetch --force
```

| Flag | Default | Description |
|------|---------|-------------|
| `--lite` / `--no-lite` | lite on | Include Planck TT + ΛCDM baseline when no IDs given |
| `--wmap` | off | Also fetch WMAP K-band map |
| `--planck` | off | Also fetch Planck SMICA 2048 map |
| `--gw` / `--no-gw` | gw on | Refresh GWTC JSON catalog |
| `--force` | off | Re-download even if cache entry is fresh |

### Pipeline

```bash
# WMAP K-band → NSIDE 128 RBLE scan (first run downloads map)
poetry run polomni data pipeline

# Fast smoke test
poetry run polomni data pipeline --nside 64 --nulls 10

# Planck SMICA (heavy)
poetry run polomni data pipeline --planck --nside 128

# Custom map product
poetry run polomni data pipeline --map-product wmap_k_band --nside 64
```

Reports are written to `data/reports/rble_<product>_<timestamp>.json`.

### Scan with cached real map

```bash
poetry run polomni scan --real --nside 64 --nulls 20
poetry run polomni scan --real --map-product wmap_k_band --nside 128
```

---

## Cache

### Layout

```
data/cache/
├── manifest.json
├── planck_cmb_tt_power/planck_cmb_tt_power.txt
├── planck_lcdm_baseline/planck_lcdm_baseline_theory_cl.txt
├── wmap_k_band/wmap_9yr_k_band.fits
├── gwtc_events/gwtc_events.json
└── …
```

Each product is stored under `<cache_root>/<product_id>/`. The manifest records fetch time, URL, size, and optional ETag/SHA256.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POLOMNI_DATA_CACHE` | `./data/cache` | Override cache root directory |

Example:

```bash
export POLOMNI_DATA_CACHE=/mnt/cosmology/polomni-cache
poetry run polomni data fetch
```

### Freshness

Products re-fetch when older than their configured `refresh_hours` (lite: ~30 days, maps: ~1 year). Use `--force` to bypass freshness checks.

Implementation: `src/polomni/observatory/pipeline/cache.py`, `downloader.py`

---

## Watch Loop

Poll GWOSC on an interval and optionally re-run the RBLE scan when new events appear:

```bash
# Poll every 5 minutes, 3 cycles
poetry run polomni data watch --interval 300 --iterations 3

# Re-scan on new GW events (60 s poll)
poetry run polomni data watch --scan-on-gw --interval 60

# Lower NSIDE for faster scans during watch
poetry run polomni data watch --nside 64 --iterations 5
```

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | 300 | Poll interval in seconds |
| `--iterations` | unlimited | Max poll cycles |
| `--nside` | 128 | HEALPix resolution for scans |
| `--scan-on-gw` | off | Re-run pipeline when new GW events detected |

The first watch iteration always runs an RBLE scan; subsequent scans depend on `--scan-on-gw` and new event detection.

Implementation: `src/polomni/observatory/pipeline/scheduler.py`

### Python API

```python
from polomni.observatory.pipeline.processor import run_rble_pipeline
from polomni.observatory.pipeline.scheduler import watch_realtime

result = run_rble_pipeline(
    map_product_id="wmap_k_band",
    target_nside=64,
    null_ensemble=10,
    report_dir="data/reports",
)
print(result.detection.rble_score, result.report_path)

for event in watch_realtime(interval_seconds=60, max_iterations=2):
    print(event.kind, event.message)
```

---

## REST API Alternative

The same operations are available over HTTP when `polomni serve` is running. See [api_reference.md](./api_reference.md) and [experiments/08_api_workflow.ipynb](../../experiments/08_api_workflow.ipynb).

---

## Troubleshooting

### Network / fetch failures

**Symptom:** `ConnectionError` or timeout during `polomni data fetch`.

- Verify outbound HTTPS to `irsa.ipac.caltech.edu`, `lambda.gsfc.nasa.gov`, and `gwosc.org`.
- Retry with `--force` after a partial download.
- Check disk space before fetching `--wmap` (~100 MB) or `--planck` (~384 MB).

### Missing WMAP map for pipeline

**Symptom:** Pipeline fails or downloads unexpectedly on first run.

```bash
poetry run polomni data fetch --wmap
poetry run polomni data status   # confirm wmap_k_band is cached
```

### GWTC not cached (API 404)

**Symptom:** `GET /data/gw/events` returns 404.

```bash
poetry run polomni data fetch --no-lite   # refreshes GWTC only if no product IDs
# or
poetry run polomni data fetch gwtc_events  # if exposed via fetch
poetry run polomni data fetch              # default includes GW refresh
```

### HEALPix / FITS errors

**Symptom:** `healpy` or `astropy` import or read errors.

```bash
poetry install              # ensures healpy + astropy
poetry run polomni info     # confirms healpy/astropy versions
```

### Slow pipeline at NSIDE 128+

Use `--nside 64 --nulls 10` for smoke tests. Production scans at NSIDE 512+ require hierarchical search (see [cmb_data_pipeline.md](./cmb_data_pipeline.md#hierarchical-sky-search)).

### Stale cache

```bash
poetry run polomni data fetch --force
rm -rf data/cache/gwtc_events   # force GW re-pull
```

### Permission errors on cache directory

Ensure `POLOMNI_DATA_CACHE` (or `data/cache/`) is writable by the current user.

---

## Related

- [cmb_data_pipeline.md](./cmb_data_pipeline.md) — full CMB scoring pipeline
- [../architecture/DATA_PIPELINE.md](../architecture/DATA_PIPELINE.md) — component architecture
- [experiments/07_real_data_pipeline.ipynb](../../experiments/07_real_data_pipeline.ipynb) — notebook walkthrough
