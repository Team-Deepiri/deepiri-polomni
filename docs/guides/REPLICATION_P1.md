# P1 Independent Replication (Gate 5)

A stranger with **no access to our notebooks** must reproduce the blind Planck holdout metrics from public data alone.

## Quick verify (cached data already present)

```bash
poetry install --with dev
poetry run polomni data fetch --wmap --planck
poetry run polomni study run p1 --blind    # if RESULT.json missing
poetry run polomni study replicate         # Gate 5 verify vs golden
poetry run polomni study gates --full --replicate
```

`RESULT.json` is sealed after the canonical blind run. Use
`polomni study replicate --rerun` for an intentional rerun; it writes
`data/studies/p1_holdout/replication/RERUN_RESULT.json`.

## Full replication from scratch

```bash
make reproduce-p1
poetry run polomni study replicate
```

## Docker (pinned image)

```bash
docker compose -f docker/docker-compose.yml build polomni-reproduce
docker compose -f docker/docker-compose.yml --profile reproduce run --rm polomni-reproduce
```

Image tag: `deepiri/polomni-reproduce:p1-v1.0.0`

## Frozen inputs

| Artifact | Path |
|----------|------|
| Pre-registration | `docs/studies/P1_CMB_RADON_SCAR_PREREG.md` |
| Study config | `data/studies/p1_holdout/study_config.json` |
| Golden reference | `data/studies/p1_holdout/golden_holdout_v1.json` |

See `docs/REPLICATION.md` for the full replication workflow.
