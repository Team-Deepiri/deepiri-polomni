"""Cosmos lab — real-sky data visualization and live verification API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import StreamingResponse

from polomni.viz.cosmos.serializers import (
    cosmos_axis_profile_payload,
    cosmos_compare_payload,
    cosmos_histogram_payload,
    cosmos_live_snapshot,
    cosmos_null_tiers_payload,
    cosmos_power_spectrum_payload,
    cosmos_sky_payload,
    cosmos_study_payload,
)
from polomni.viz.cosmos.verification import (
    is_running,
    progress_events,
    run_full_verification,
)

router = APIRouter(tags=["cosmos"])

_verify_state: dict = {"running": False, "last": None, "error": None}


@router.get("/sky")
def get_cosmos_sky(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=256),
    force: bool = Query(default=False),
) -> dict:
    return cosmos_sky_payload(map_product_id=map_product, nside=nside, force=force)


@router.get("/power-spectrum")
def get_power_spectrum() -> dict:
    return cosmos_power_spectrum_payload()


@router.get("/study")
def get_study_status() -> dict:
    return cosmos_study_payload()


@router.get("/compare")
def get_compare(nside: int = Query(default=64, ge=16, le=128)) -> dict:
    return cosmos_compare_payload(nside=nside)


@router.get("/null-histogram")
def get_null_histogram(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=128),
    n_ensemble: int = Query(default=35, ge=10, le=60),
) -> dict:
    return cosmos_histogram_payload(
        map_product_id=map_product,
        nside=nside,
        n_ensemble=n_ensemble,
    )


@router.get("/axis-profile")
def get_axis_profile(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=128),
) -> dict:
    return cosmos_axis_profile_payload(map_product_id=map_product, nside=nside)



@router.get("/tomogram")
def get_tomogram(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=128),
    n_eta: int = Query(default=128, ge=32, le=256),
) -> dict:
    from polomni.viz.cosmos.tomography import cosmos_tomogram_payload

    return cosmos_tomogram_payload(map_product_id=map_product, nside=nside, n_eta=n_eta)


@router.get("/landscape")
def get_landscape(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=128),
    nside_dirs: int = Query(default=8, ge=4, le=16),
) -> dict:
    from polomni.viz.cosmos.tomography import cosmos_landscape_payload

    return cosmos_landscape_payload(
        map_product_id=map_product,
        nside=nside,
        nside_dirs=nside_dirs,
    )


@router.get("/null-tiers")
def get_null_tiers(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=128),
) -> dict:
    return cosmos_null_tiers_payload(map_product_id=map_product, nside=nside)


@router.get("/snapshot")
def get_snapshot() -> dict:
    return cosmos_live_snapshot()


def _run_verify(blind: bool) -> None:
    global _verify_state
    _verify_state["running"] = True
    _verify_state["error"] = None
    try:
        _verify_state["last"] = run_full_verification(blind=blind, strict_prove=True)
    except Exception as exc:
        _verify_state["error"] = str(exc)
    finally:
        _verify_state["running"] = False


@router.post("/verify")
def post_verify(
    background: BackgroundTasks,
    blind: bool = Query(default=False),
) -> dict:
    if _verify_state["running"] or is_running():
        return {"status": "running", "message": "Verification already in progress"}
    background.add_task(_run_verify, blind)
    return {"status": "started", "blind": blind}


@router.get("/verify/status")
def verify_status() -> dict:
    return {
        "running": _verify_state["running"] or is_running(),
        "error": _verify_state["error"],
        "has_result": _verify_state["last"] is not None,
        "last_completed_at": (_verify_state["last"] or {}).get("completed_at"),
        "progress_count": len(progress_events()),
    }


@router.get("/verify/result")
def verify_result() -> dict:
    if _verify_state["last"] is None:
        return {"ready": False}
    return {"ready": True, **_verify_state["last"]}


@router.get("/verify/progress")
async def verify_progress_stream(
    interval: float = Query(default=1.0, ge=0.5, le=10.0),
    ticks: int = Query(default=600, ge=1, le=3600),
) -> StreamingResponse:
    """SSE stream of verification step events during long runs."""

    async def gen() -> AsyncIterator[str]:
        seen = 0
        for _ in range(ticks):
            events = progress_events()
            if len(events) > seen:
                for ev in events[seen:]:
                    yield f"data: {json.dumps(ev)}\n\n"
                seen = len(events)
            if not is_running() and not _verify_state["running"] and seen > 0:
                yield f"data: {json.dumps({'step': 'idle', 'message': 'done'})}\n\n"
                break
            await asyncio.sleep(interval)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/live")
async def cosmos_live_stream(
    interval: float = Query(default=8.0, ge=2.0, le=60.0),
    ticks: int = Query(default=30, ge=1, le=120),
) -> StreamingResponse:
    async def gen() -> AsyncIterator[str]:
        for _ in range(ticks):
            snap = cosmos_live_snapshot()
            snap["verify_running"] = _verify_state["running"] or is_running()
            yield f"data: {json.dumps(snap)}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
