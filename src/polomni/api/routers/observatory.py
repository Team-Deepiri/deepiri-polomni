"""CMB scan, pipeline, and report listing routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from polomni.api.deps import get_cache
from polomni.api.schemas import (
    CompareRequest,
    CompareResponse,
    PipelineRequest,
    PipelineResponse,
    ReportSummary,
    ReportsListResponse,
    ScanRequest,
    ScanResponse,
)
from polomni.observatory.reports.comparison import compare_reports, load_report
from polomni.observatory.ingest.healpix_loader import (
    downsample_map,
    load_healpix_map,
    synthetic_cmb_map,
)
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.processor import run_rble_pipeline
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import compute_rble_signature

router = APIRouter(tags=["observatory"])

DEFAULT_REPORT_DIR = Path("data/reports")


def _detection_to_scan_response(detection) -> ScanResponse:
    return ScanResponse(
        rble_score=detection.rble_score,
        preferred_axis=detection.preferred_axis,
        n_hat=detection.n_hat,
        null_sigma=detection.null_sigma,
        falsification_flags=detection.falsification_flags,
        metadata=detection.metadata,
        timestamp=detection.timestamp,
    )


@router.post("/scan", response_model=ScanResponse)
def scan(
    body: ScanRequest,
    cache: Annotated[DataCache, Depends(get_cache)],
) -> ScanResponse:
    """Run an RBLE scar scan on synthetic or cached real-sky data."""
    if body.synthetic:
        cmb = synthetic_cmb_map(body.nside, seed=body.seed)
        null_nside = body.nside
    elif body.map_product_id is not None:
        product = get_product(body.map_product_id)
        fetched = fetch_product(product, cache, force=False)
        raw = load_healpix_map(fetched.path, field="T")
        cmb = downsample_map(raw, body.nside)
        null_nside = body.nside
    elif body.map_path is not None:
        cmb = load_healpix_map(Path(body.map_path), field="T")
        null_nside = 64
    else:
        cmb = synthetic_cmb_map(body.nside, seed=body.seed)
        null_nside = body.nside

    detection = compute_rble_signature(cmb)
    null_maps = generate_null_ensemble(body.nulls, null_nside, seed=body.seed + 1)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]
    mu = float(sum(null_scores) / len(null_scores))
    sigma = float((sum((s - mu) ** 2 for s in null_scores) / len(null_scores)) ** 0.5)
    if sigma > 0:
        detection.null_sigma = (detection.rble_score - mu) / sigma

    return _detection_to_scan_response(detection)


@router.post("/pipeline", response_model=PipelineResponse)
def pipeline(
    body: PipelineRequest,
    cache: Annotated[DataCache, Depends(get_cache)],
) -> PipelineResponse:
    """Run the full RBLE observatory pipeline using cached data."""
    result = run_rble_pipeline(
        cache=cache,
        map_product_id=body.map_product,
        force_fetch=body.force,
        target_nside=body.nside,
        null_ensemble=body.nulls,
        report_dir=DEFAULT_REPORT_DIR,
        fetch_gw=not body.force,
    )
    det = result.detection
    return PipelineResponse(
        ran_at=result.ran_at,
        map_product_id=result.map_product_id,
        nside_used=result.nside_used,
        rble_score=det.rble_score,
        preferred_axis=det.preferred_axis,
        n_hat=det.n_hat,
        null_sigma=det.null_sigma,
        falsification_flags=det.falsification_flags,
        metadata=det.metadata,
        timestamp=det.timestamp,
        planck_lambda=result.planck_lambda,
        report_path=str(result.report_path) if result.report_path else None,
        gw_new_events=len(result.ingest.gw_new_events),
    )


@router.get("/reports", response_model=ReportsListResponse)
def reports() -> ReportsListResponse:
    """List JSON detection reports in data/reports/."""
    report_dir = DEFAULT_REPORT_DIR
    if not report_dir.exists():
        return ReportsListResponse(reports=[])

    items: list[ReportSummary] = []
    for path in sorted(report_dir.glob("*.json"), reverse=True):
        items.append(
            ReportSummary(
                filename=path.name,
                path=str(path),
                size_bytes=path.stat().st_size,
            )
        )
    return ReportsListResponse(reports=items)


@router.post("/compare", response_model=CompareResponse)
def compare(body: CompareRequest) -> CompareResponse:
    """Compare two saved detection reports."""
    cmp = compare_reports(load_report(body.report_a), load_report(body.report_b))
    return CompareResponse(**cmp)
