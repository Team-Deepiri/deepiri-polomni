# REST API Reference

HTTP API for the Deepiri Polomni lab. Start the server with:

```bash
poetry run polomni serve
# Default: http://127.0.0.1:8091
```

OpenAPI docs (interactive): `http://127.0.0.1:8091/docs`

Implementation: `src/polomni/api/` · Schemas: `src/polomni/api/schemas.py`

---

## Health

### `GET /`

Service metadata.

**Response** `200`

```json
{
  "name": "deepiri-polomni",
  "framework": "RBLE"
}
```

### `GET /health`

Liveness probe for orchestrators and CI.

**Response** `200`

```json
{
  "status": "ok",
  "service": "polomni-lab"
}
```

---

## Data (`/data`)

### `GET /data/catalog`

List all fetchable CATALOG data products.

**Response** `200` — array of:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Product ID (e.g. `wmap_k_band`) |
| `name` | string | Human-readable name |
| `tier` | string | `lite`, `standard`, or `heavy` |
| `mission` | string | Source mission |
| `description` | string | Short description |
| `kind` | string | `fits`, `txt`, or `json` |

**Example**

```bash
curl -s http://127.0.0.1:8091/data/catalog | jq '.[0]'
```

---

### `GET /data/status`

Return cache status for every catalog product plus GWTC.

**Response** `200` — array of:

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | string | Product ID |
| `cached` | boolean | Whether file exists on disk |
| `path` | string \| null | Absolute path when cached |
| `size_bytes` | integer \| null | File size when cached |

**Example**

```bash
curl -s http://127.0.0.1:8091/data/status | jq '.[] | select(.cached)'
```

---

### `POST /data/fetch`

Download one or more products into the local cache.

**Request body**

```json
{
  "product_ids": ["planck_cmb_tt_power", "planck_lcdm_baseline"],
  "force": false,
  "fetch_gw": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `product_ids` | string[] | required | IDs from `/data/catalog` |
| `force` | boolean | `false` | Re-download ignoring freshness |
| `fetch_gw` | boolean | `true` | Also refresh GWTC JSON catalog |

**Response** `200`

```json
{
  "results": [
    {
      "product_id": "planck_cmb_tt_power",
      "path": "/path/to/data/cache/planck_cmb_tt_power/planck_cmb_tt_power.txt",
      "bytes_written": 12345,
      "from_cache": true
    }
  ],
  "gw_events_count": 93
}
```

**Errors**

| Status | Condition |
|--------|-----------|
| `400` | Unknown `product_id` |

**Example**

```bash
curl -s -X POST http://127.0.0.1:8091/data/fetch \
  -H 'Content-Type: application/json' \
  -d '{"product_ids":["planck_cmb_tt_power","planck_lcdm_baseline"],"fetch_gw":true}'
```

---

### `GET /data/gw/events`

Load cached GWTC catalog and return event count plus recent entries.

**Response** `200`

```json
{
  "count": 93,
  "recent": [
    {
      "name": "GW150914",
      "gps": 1126259462.4,
      "catalog": "GWTC",
      "detectors": ["H1", "L1"]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Total events in cached catalog |
| `recent` | array | Up to 10 most recent events |

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | GWTC not cached — call `POST /data/fetch` with `fetch_gw: true` first |

**Example**

```bash
curl -s http://127.0.0.1:8091/data/gw/events | jq '.count'
```

---

## Observatory (`/observatory`)

### `POST /observatory/scan`

Run an RBLE scar scan on synthetic or cached real-sky data.

**Request body**

```json
{
  "nside": 64,
  "synthetic": true,
  "map_product_id": null,
  "nulls": 20,
  "seed": 42,
  "map_path": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `nside` | integer | `64` | HEALPix resolution |
| `synthetic` | boolean | `true` | Generate Gaussian CMB instead of real map |
| `map_product_id` | string \| null | `null` | Cached product ID when `synthetic: false` |
| `nulls` | integer | `20` | Null ensemble size for σ estimate |
| `seed` | integer | `42` | RNG seed for synthetic map and nulls |
| `map_path` | string \| null | `null` | Local FITS path (alternative to product ID) |

**Response** `200`

```json
{
  "rble_score": 1.234,
  "preferred_axis": [0.0, 0.0, 1.0],
  "n_hat": [0.0, 0.0, 1.0],
  "null_sigma": 2.5,
  "falsification_flags": {
    "radon_anisotropic": true,
    "te_coupling_stub": true,
    "null_rejected_stub": true
  },
  "metadata": {"map_rms": 1e-5, "npix": 49152},
  "timestamp": "2026-06-28T12:00:00Z"
}
```

**Example — synthetic smoke scan**

```bash
curl -s -X POST http://127.0.0.1:8091/observatory/scan \
  -H 'Content-Type: application/json' \
  -d '{"synthetic":true,"nside":32,"nulls":5}'
```

**Example — cached WMAP map**

```bash
curl -s -X POST http://127.0.0.1:8091/observatory/scan \
  -H 'Content-Type: application/json' \
  -d '{"synthetic":false,"map_product_id":"wmap_k_band","nside":64,"nulls":10}'
```

---

### `POST /observatory/pipeline`

Run the full ingest → load → downsample → RBLE score → report pipeline.

**Request body**

```json
{
  "map_product": "wmap_k_band",
  "nside": 64,
  "nulls": 10,
  "force": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `map_product` | string \| null | `null` | Map product ID (default: `wmap_k_band`) |
| `nside` | integer | `128` | Target HEALPix NSIDE |
| `nulls` | integer | `30` | Null ensemble size |
| `force` | boolean | `false` | Force re-fetch before scan |

**Response** `200`

```json
{
  "ran_at": "2026-06-28T14:00:00Z",
  "map_product_id": "wmap_k_band",
  "nside_used": 64,
  "rble_score": 5.05,
  "preferred_axis": [-0.87, 0.50, 0.04],
  "n_hat": [-0.87, 0.50, 0.04],
  "null_sigma": 78.85,
  "falsification_flags": {"radon_anisotropic": true},
  "metadata": {"map_rms": 2.84, "npix": 49152},
  "timestamp": "2026-06-28T14:00:00Z",
  "planck_lambda": 0.308,
  "report_path": "data/reports/rble_wmap_k_band_20260628T140000Z.json",
  "gw_new_events": 0
}
```

**Example**

```bash
curl -s -X POST http://127.0.0.1:8091/observatory/pipeline \
  -H 'Content-Type: application/json' \
  -d '{"map_product":"wmap_k_band","nside":64,"nulls":10}'
```

---

### `GET /observatory/reports`

List JSON detection reports in `data/reports/`.

**Response** `200`

```json
{
  "reports": [
    {
      "filename": "rble_wmap_k_band_20260628T140000Z.json",
      "path": "data/reports/rble_wmap_k_band_20260628T140000Z.json",
      "size_bytes": 512
    }
  ]
}
```

**Example**

```bash
curl -s http://127.0.0.1:8091/observatory/reports | jq '.reports[0]'
```

---

## Stream (`/stream`)

### `GET /stream/gw/poll`

Server-Sent Events (SSE) stream of GW catalog poll events.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interval` | float | `5.0` | Seconds between polls (1–60) |
| `max_events` | integer | `3` | Maximum SSE events before stream closes (1–10) |

**Response** `200` — `Content-Type: text/event-stream`

Each event:

```
data: {"timestamp":"2026-06-28T12:00:00+00:00","kind":"gw_poll","results_count":93,"new_events":0,"message":"GWTC catalog: 93 events, 0 new"}

```

**Example**

```bash
curl -N 'http://127.0.0.1:8091/stream/gw/poll?interval=2&max_events=2'
```

Use `-N` to disable buffering for live SSE output.

---

## Error Handling

All endpoints return standard HTTP status codes. Validation errors from FastAPI/Pydantic return `422` with a detail array. Business errors (e.g. missing GW cache) return `4xx` with a `detail` string.

---

## CORS

The API enables CORS for all origins in development (`allow_origins=["*"]`). Restrict origins in production deployments.

---

## Related

- [real_time_data.md](./real_time_data.md) — CLI equivalent of data/pipeline operations
- [../architecture/DATA_PIPELINE.md](../architecture/DATA_PIPELINE.md) — pipeline architecture
- [experiments/08_api_workflow.ipynb](../../experiments/08_api_workflow.ipynb) — curl walkthrough notebook
