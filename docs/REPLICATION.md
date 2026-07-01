# P1 Replication Package

Reproduce the pre-registered Planck blind holdout analysis on public NASA/ESA data.

## Prerequisites

- Python 3.10+, Poetry
- ~500 MB disk for WMAP + Planck FITS caches
- Network for first-time data fetch

## One command

```bash
make reproduce-p1
```

Or:

```bash
bash scripts/reproduce-p1.sh
```

This runs:

1. `poetry install --with dev`
2. `polomni data fetch` (WMAP Ka + Planck SMICA if missing)
3. **Gates 1–3** — pre-reg frozen, injection recovery, cache ready
4. **WMAP calibration** run (`study run p1 --calibration`)
5. **Gate 4** — blind Planck SMICA holdout (`study run p1 --blind`)
6. SHA256 manifest in `data/studies/p1_holdout/replication/`

## Step-by-step

```bash
poetry install --with dev
poetry run polomni data fetch --wmap --planck
poetry run polomni study gates
poetry run pytest tests/observatory/test_p1_injection_recovery.py -m slow -q
poetry run polomni study run p1 --calibration
poetry run polomni study run p1 --blind
poetry run polomni study gates --full
```

## Frozen artifacts

| File | Role |
|------|------|
| `docs/studies/P1_CMB_RADON_SCAR_PREREG.md` | Pre-registration (before holdout) |
| `data/studies/p1_holdout/study_config.json` | Sealed analysis parameters |
| `data/studies/p1_holdout/RESULT.json` | Calibration or holdout output |
| `data/cache/manifest.json` | SHA256 of downloaded mission files |

## Docker

```bash
# Build lab image
docker compose -f docker/docker-compose.yml build polomni-lab

# Run full P1 replication (mounts cache + studies volumes)
docker compose -f docker/docker-compose.yml --profile reproduce run --rm polomni-reproduce
```

## Interpreting results

- **`p1_supported: true`** — Bonferroni + all null tiers (N0/N1/N2) + TE cross-check passed on holdout
- **`p1_falsified: true`** — Holdout run completed; P1 hypothesis not supported (valid scientific outcome)

A falsified holdout is **not** a failed replication — it means the pipeline ran honestly on locked Planck data.

## Data sources (public)

- WMAP Ka: `lambda.gsfc.nasa.gov` (DR5)
- Planck SMICA: `irsa.ipac.caltech.edu` (Planck Release 3)
- GWOSC: `gwosc.org/api/v2`

URLs are pinned in `src/polomni/observatory/pipeline/catalog.py`.
