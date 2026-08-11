"""GWOSC gravitational-wave transient catalog (real-time JSON API)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import (
    GWOSC_CATALOG_URL,
    GWOSC_EVENTS_PRODUCT_ID,
    gwosc_event_detail_url,
)
from polomni.observatory.pipeline.config import get_settings

# Approximate IFO boresight unit vectors (lat/lon → Cartesian, degrees).
_DETECTOR_AXES: dict[str, np.ndarray] = {
    "H1": np.array([0.954, -0.257, 0.151]),
    "L1": np.array([0.455, -0.794, 0.401]),
    "V1": np.array([0.374, 0.851, 0.369]),
}


class GWEvent(BaseModel):
    name: str
    gps: float
    catalog: str
    detectors: list[str] = Field(default_factory=list)
    version: int = 1
    network_axis: list[float] | None = None


class GWEventDetail(BaseModel):
    name: str
    grace_id: str | None = None
    run: str | None = None
    aliases: list[str] = Field(default_factory=list)
    versions: list[dict[str, Any]] = Field(default_factory=list)


class GWCatalogSnapshot(BaseModel):
    fetched_at: datetime
    results_count: int
    events: list[GWEvent]


def network_axis_from_detectors(detectors: list[str]) -> np.ndarray | None:
    """Stub: mean detector-network axis from participating IFO codes."""
    vectors = [_DETECTOR_AXES[code] for code in detectors if code in _DETECTOR_AXES]
    if not vectors:
        return None
    axis = np.mean(vectors, axis=0)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-15:
        return None
    return axis / norm


def fetch_gw_event_detail(
    event_name: str,
    *,
    timeout: float | None = None,
) -> GWEventDetail:
    """Fetch single-event metadata from GWOSC API v2."""
    timeout = timeout if timeout is not None else get_settings().fetch_timeout
    url = gwosc_event_detail_url(event_name)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload: dict[str, Any] = json.loads(resp.read().decode())
    return GWEventDetail(
        name=payload["name"],
        grace_id=payload.get("grace_id"),
        run=payload.get("run"),
        aliases=list(payload.get("aliases", [])),
        versions=list(payload.get("versions", [])),
    )


def fetch_gwtc_events(
    cache: DataCache | None = None,
    *,
    max_pages: int = 5,
    timeout: float | None = None,
) -> GWCatalogSnapshot:
    """Paginate GWOSC GWTC events API and cache merged JSON snapshot."""
    cache = cache or DataCache()
    timeout = timeout if timeout is not None else get_settings().fetch_timeout
    all_events: list[GWEvent] = []
    url: str | None = GWOSC_CATALOG_URL
    pages = 0

    while url and pages < max_pages:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode())
        for row in payload.get("results", []):
            detectors = list(row.get("detectors", []))
            axis = network_axis_from_detectors(detectors)
            all_events.append(
                GWEvent(
                    name=row["name"],
                    gps=float(row["gps"]),
                    catalog=row.get("catalog", "GWTC"),
                    detectors=detectors,
                    version=int(row.get("version", 1)),
                    network_axis=None if axis is None else axis.tolist(),
                )
            )
        url = payload.get("next")
        pages += 1

    snapshot = GWCatalogSnapshot(
        fetched_at=datetime.now(timezone.utc),
        results_count=len(all_events),
        events=all_events,
    )

    dest_dir = cache.root / GWOSC_EVENTS_PRODUCT_ID
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "gwtc_events.json"
    cache.store_text(
        GWOSC_EVENTS_PRODUCT_ID,
        dest,
        snapshot.model_dump_json(indent=2),
        GWOSC_CATALOG_URL,
        extra={"results_count": snapshot.results_count},
    )
    return snapshot


def load_cached_gwtc(cache: DataCache | None = None) -> GWCatalogSnapshot | None:
    cache = cache or DataCache()
    path = cache.resolved_path(GWOSC_EVENTS_PRODUCT_ID)
    if path is None:
        return None
    return GWCatalogSnapshot.model_validate_json(path.read_text())


def new_events_since(
    previous: GWCatalogSnapshot | None,
    current: GWCatalogSnapshot,
) -> list[GWEvent]:
    if previous is None:
        return current.events
    prev_names = {e.name for e in previous.events}
    return [e for e in current.events if e.name not in prev_names]
