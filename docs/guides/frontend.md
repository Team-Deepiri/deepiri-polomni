# Polomni Multiverse Frontend

React + Vite visualization app for RBLE multiverse science: district graphs, Kähler landscape, scar sphere, stream flux, falsification panel, and live math proofs.

## Development

Terminal 1 — API:

```bash
poetry run polomni serve --port 8091
```

Terminal 2 — frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies API routes to :8091.

Or use:

```bash
poetry run polomni frontend dev
```

## Production build

```bash
make frontend-build
poetry run polomni serve
```

Built assets in `frontend/dist/` are served at http://localhost:8091/app

## API endpoints used

| Panel | Endpoint |
|-------|----------|
| District graph | `GET /viz/district-graph` |
| Kähler landscape | `GET /viz/landscape` |
| Scar sphere | `GET /viz/scar-sphere` |
| Stream flux | `GET /viz/stream-flux` |
| Branch simplex | `GET /viz/branch-simplex` |
| Falsification | `GET /viz/falsification` |
| Proofs | `POST /math/prove`, `GET /math/proofs` |

## Docker

The lab container serves the API; build frontend on the host before `docker compose up` if you need `/app` in the container.
