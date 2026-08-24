"""Cosmos lab — real-sky data visualization and live verification API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import Response, StreamingResponse

from polomni.viz.cosmos.catalog_overlay import cosmos_world_payload
from polomni.viz.cosmos.raster import sky_overlays_geojson, sky_raster_png
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
from polomni.viz.cosmos.worlds import exoplanet_world_payload

router = APIRouter(tags=["cosmos"])

_verify_state: dict = {"running": False, "last": None, "error": None}


@router.get("/sky")
def get_cosmos_sky(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=256),
    force: bool = Query(default=False),
) -> dict:
    return cosmos_sky_payload(map_product_id=map_product, nside=nside, force=force)


@router.get("/sky/raster")
def get_cosmos_sky_raster(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=256),
    width: int = Query(default=1024, ge=256, le=4096),
    height: int = Query(default=512, ge=128, le=2048),
    force: bool = Query(default=False),
) -> Response:
    """Equirectangular PNG of real CMB sky for MapLibre image source."""
    png = sky_raster_png(
        map_product_id=map_product,
        nside=nside,
        width=width,
        height=height,
        force=force,
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=600"},
    )


@router.get("/sky/overlays")
def get_cosmos_sky_overlays(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=256),
    force: bool = Query(default=False),
) -> dict:
    """GeoJSON scar ring + preferred axis for MapLibre overlay layers."""
    return sky_overlays_geojson(map_product_id=map_product, nside=nside, force=force)


@router.get("/sky/world")
def get_cosmos_sky_world(
    map_product: str = Query(default="wmap_k_band"),
    nside: int = Query(default=64, ge=16, le=256),
    frame: str = Query(default="galactic", pattern="^(galactic|equatorial)$"),
    force: bool = Query(default=False),
) -> dict:
    """Real-sky world model: HiPS surveys, GW/SDSS catalogs, RBLE CV overlays."""
    return cosmos_world_payload(
        map_product_id=map_product,
        nside=nside,
        frame=frame,  # type: ignore[arg-type]
        force=force,
    )


@router.get("/worlds")
def get_cosmos_worlds(
    nside: int = Query(default=32, ge=8, le=128),
    weight: str = Query(default="count", pattern="^(count|teff|period)$"),
    n_ensemble: int = Query(default=40, ge=5, le=120),
    n_null: int = Query(default=100, ge=10, le=400),
    max_points: int = Query(default=1500, ge=200, le=6334),
) -> dict:
    """World Atlas — RBLE scan over real NASA exoplanet sky positions.

    Includes the footprint-matched null significance, the per-method
    preferred-axis audit, the world-dipole cosmic-rest-frame test, and the
    world-sky angular power spectrum with its uniform-within-footprint null.
    """
    from polomni.viz.cosmos.worlds import exoplanet_world_payload

    return exoplanet_world_payload(
        nside=nside,
        weight=weight,  # type: ignore[arg-type]
        n_ensemble=n_ensemble,
        n_null=n_null,
        max_points=max_points,
    )


@router.get("/power-spectrum")
def get_power_spectrum() -> dict:
    return cosmos_power_spectrum_payload()


@router.get("/cross-sky")
def get_cross_sky(
    min_objects: int = Query(default=20, ge=1, le=100000),
) -> dict:
    """Cross-sky axis comparison across independent sky datasets.

    A scar locked to a single preferred axis must appear in every sky. This
    compares dipoles across the cached independent skies (exoplanets, SDSS
    galaxies, GW events) — GW events whose ``network_axis`` is instrument
    geometry rather than sky direction are excluded with a note.
    """
    from polomni.observatory.pipeline.sources.cross_sky import cross_sky_report

    return cross_sky_report(min_objects=min_objects)


@router.get("/scar-consensus")
def get_scar_consensus(
    nside: int = Query(default=32, ge=8, le=64),
    n_null: int = Query(default=16, ge=4, le=64),
    seed: int = Query(default=0, ge=0),
    refresh_sdss: bool = Query(default=False),
) -> dict:
    """Three-gate multi-survey scar consensus (CMB-anchored, footprint-null).

    Dipole agreement is intentionally *not* a detection gate. Requires
    intra-WMAP axis agreement, catalog S_RBLE at the CMB consensus axis above
    footprint nulls, and residual nematic axes near that consensus.
    """
    from polomni.observatory.pipeline.sources.multi_survey_scar import (
        multi_survey_scar_report,
    )

    return multi_survey_scar_report(
        nside=nside,
        n_null=n_null,
        seed=seed,
        refresh_sdss=refresh_sdss,
    )


@router.get("/bubble-search")
def get_bubble_search(
    nside: int = Query(default=128, ge=32, le=256),
    n_null: int = Query(default=16, ge=4, le=64),
    n_null_rank1: int = Query(default=16, ge=4, le=64),
) -> dict:
    """Bubble-collision search — the falsifiable multiverse observable.

    Scans a real CMB map for circular temperature edges, the signature of a
    bubble colliding with ours in eternal inflation. Compares the strongest
    edge against a C_ℓ-matched + mask-matched Gaussian null (look-elsewhere
    corrected) and reports an honest verdict. Also runs the rank-1 harmonic
    axis search: a collision about n̂_c has ``a_lm = C_l·Y_lm(n̂_c)`` at every
    l, so the m=0 power fraction at the collision axis is 1 at every multipole
    (vs the isotropic 1/(2l+1)).
    """
    from polomni.observatory.pipeline.sources.bubble_collisions import bubble_collision_report

    return bubble_collision_report(nside=nside, n_null=n_null, n_null_rank1=n_null_rank1)


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
