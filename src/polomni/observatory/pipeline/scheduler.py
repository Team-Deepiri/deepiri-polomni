"""Real-time polling loop for online cosmology data sources."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.config import get_settings
from polomni.observatory.pipeline.events import EventLog, pipeline_event
from polomni.observatory.pipeline.processor import PipelineResult, run_rble_pipeline
from polomni.observatory.pipeline.sources.gwosc import (
    fetch_gwtc_events,
    load_cached_gwtc,
    new_events_since,
)


@dataclass
class WatchEvent:
    timestamp: datetime
    kind: str
    message: str
    pipeline_result: PipelineResult | None = None


def _default_event_log(cache: DataCache) -> EventLog:
    return EventLog(cache.root / "events.jsonl")


def _emit_watch_event(
    evt: WatchEvent,
    *,
    event_log: EventLog | None,
    on_event: Callable[[WatchEvent], None] | None,
) -> None:
    if event_log is not None:
        payload: dict = {"message": evt.message}
        if evt.pipeline_result is not None:
            payload["map_product_id"] = evt.pipeline_result.map_product_id
            payload["rble_score"] = evt.pipeline_result.detection.rble_score
        event_log.append(
            pipeline_event(
                evt.kind,
                **payload,
            )
        )
    if on_event is not None:
        on_event(evt)


def _poll_gw_catalog(
    cache: DataCache,
    *,
    event_log: EventLog | None,
    on_event: Callable[[WatchEvent], None] | None,
) -> tuple[WatchEvent, list]:
    now = datetime.now(timezone.utc)
    prev = load_cached_gwtc(cache)
    snap = fetch_gwtc_events(cache)
    fresh = new_events_since(prev, snap)

    evt = WatchEvent(
        timestamp=now,
        kind="gw_poll",
        message=f"GWTC catalog: {snap.results_count} events, {len(fresh)} new",
    )
    _emit_watch_event(evt, event_log=event_log, on_event=on_event)
    return evt, fresh


def poll_once(
    *,
    cache: DataCache | None = None,
    event_log: EventLog | None = None,
    on_event: Callable[[WatchEvent], None] | None = None,
) -> WatchEvent:
    """Run a single GWOSC catalog poll without entering the watch loop."""
    cache = cache or DataCache()
    log = event_log if event_log is not None else _default_event_log(cache)
    evt, _ = _poll_gw_catalog(cache, event_log=log, on_event=on_event)
    return evt


def watch_realtime(
    *,
    interval_seconds: float | None = None,
    max_iterations: int | None = None,
    cache: DataCache | None = None,
    on_event: Callable[[WatchEvent], None] | None = None,
    run_scan_on_gw_update: bool = False,
    target_nside: int = 128,
    event_log: EventLog | None = None,
) -> Iterator[WatchEvent]:
    """Poll GWOSC + refresh lite data on an interval (real-time ingestion loop).

    Yields :class:`WatchEvent` for each poll cycle. GW catalog is checked every
    cycle; full RBLE scan runs when ``run_scan_on_gw_update`` and new events
    appear, or on the first iteration.
    """
    cache = cache or DataCache()
    log = event_log if event_log is not None else _default_event_log(cache)
    if interval_seconds is None:
        interval_seconds = get_settings().gw_poll_interval
    iteration = 0
    first = True

    while max_iterations is None or iteration < max_iterations:
        evt, fresh = _poll_gw_catalog(cache, event_log=log, on_event=on_event)
        yield evt

        should_scan = first or (run_scan_on_gw_update and len(fresh) > 0)
        if should_scan:
            result = run_rble_pipeline(
                cache=cache,
                force_fetch=False,
                target_nside=target_nside,
                fetch_gw=False,
                event_log=log,
            )
            scan_evt = WatchEvent(
                timestamp=datetime.now(timezone.utc),
                kind="rble_scan",
                message=(
                    f"RBLE score={result.detection.rble_score:.4f} "
                    f"on {result.map_product_id} (NSIDE={result.nside_used})"
                ),
                pipeline_result=result,
            )
            _emit_watch_event(scan_evt, event_log=log, on_event=on_event)
            yield scan_evt
            first = False

        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(interval_seconds)
