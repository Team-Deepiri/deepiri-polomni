"""Server-sent event streams for real-time observatory updates."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from polomni.api.deps import get_cache
from polomni.observatory.pipeline.cache import DataCache

router = APIRouter(tags=["stream"])

try:
    from polomni.observatory.pipeline.scheduler import poll_once
except ImportError:
    from polomni.observatory.pipeline.sources.gwosc import (
        fetch_gwtc_events,
        load_cached_gwtc,
        new_events_since,
    )

    def poll_once(cache: DataCache | None = None) -> dict[str, Any]:
        """Single GW poll cycle (fallback when scheduler.poll_once is unavailable)."""
        cache = cache or DataCache()
        now = datetime.now(timezone.utc)
        prev = load_cached_gwtc(cache)
        snap = fetch_gwtc_events(cache)
        fresh = new_events_since(prev, snap)
        return {
            "timestamp": now.isoformat(),
            "kind": "gw_poll",
            "results_count": snap.results_count,
            "new_events": len(fresh),
            "message": f"GWTC catalog: {snap.results_count} events, {len(fresh)} new",
        }


def _serialize_event(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    return {
        "timestamp": getattr(event, "timestamp", datetime.now(timezone.utc)).isoformat(),
        "kind": getattr(event, "kind", "gw_poll"),
        "message": getattr(event, "message", str(event)),
    }


@router.get("/gw/poll")
async def gw_poll_stream(
    cache: Annotated[DataCache, Depends(get_cache)],
    interval: float = Query(default=5.0, ge=1.0, le=60.0),
    max_events: int = Query(default=3, ge=1, le=10),
) -> StreamingResponse:
    """SSE stream of GW catalog poll events (max 3 events in dev by default)."""

    async def event_generator() -> AsyncIterator[str]:
        emitted = 0
        while emitted < max_events:
            event = poll_once(cache=cache)
            payload = _serialize_event(event)
            yield f"data: {json.dumps(payload)}\n\n"
            emitted += 1
            if emitted >= max_events:
                break
            await asyncio.sleep(interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
