# Docker Lab Environment

Run the full Polomni lab in Docker with API, Jupyter, and optional GW watch.

## Quick start

```bash
make docker-up
# or
bash scripts/dev-up.sh
```

- **API + Dashboard:** http://localhost:8091/dashboard
- **Jupyter Lab:** http://localhost:8888
- **Health:** http://localhost:8091/health

## Services

| Service | Profile | Description |
|---------|---------|-------------|
| `polomni-lab` | default | API + Jupyter |
| `polomni-watch` | `watch` | Continuous GWOSC polling + optional RBLE re-scan |
| `polomni-lab-gpu` | `gpu` | GPU-enabled lab (optional torch) |

## Volumes

- `polomni-cache` — persistent `data/cache/` for fetched cosmology products
- `data/reports` — host-mounted detection reports

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `POLOMNI_DATA_CACHE` | `/app/data/cache` | Cache root in container |
| `POLOMNI_GW_POLL_INTERVAL` | `300` | GW watch poll seconds |

## Watch profile

```bash
docker compose -f docker/docker-compose.yml --profile watch up -d
```

Runs `polomni data watch --scan-on-gw` against the shared cache volume.
