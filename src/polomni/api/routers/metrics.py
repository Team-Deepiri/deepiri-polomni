"""Lab metrics and operational status."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends

from polomni.api.deps import get_cache
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import list_cached_products
from polomni.observatory.pipeline.sources.gwosc import load_cached_gwtc
from polomni.observatory.reports.comparison import latest_report, load_report

router = APIRouter(tags=["metrics"])

_START_TIME = time.monotonic()


@router.get("/metrics")
def metrics(cache: DataCache = Depends(get_cache)) -> dict:
    """Operational metrics for the Polomni lab."""
    cached = list_cached_products(cache)
    cache_count = sum(1 for p in cached.values() if p is not None)

    gw_count = 0
    try:
        gw_count = load_cached_gwtc(cache).results_count
    except Exception:
        pass

    report_dir = Path("data/reports")
    reports = sorted(report_dir.glob("*.json")) if report_dir.is_dir() else []
    last_score: float | None = None
    latest = latest_report(report_dir) if reports else None
    if latest is not None:
        try:
            last_score = load_report(latest).rble_score
        except Exception:
            pass

    return {
        "uptime_seconds": round(time.monotonic() - _START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache_product_count": cache_count,
        "gw_event_count": gw_count,
        "report_count": len(reports),
        "last_pipeline_score": last_score,
        "cache_dir": str(cache.root),
    }
