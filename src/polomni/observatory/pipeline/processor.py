"""End-to-end real-data RBLE observatory pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import (
    CATALOG,
    STANDARD_FETCH_IDS,
    DataProduct,
    get_product,
)
from polomni.observatory.pipeline.downloader import FetchResult, fetch_product
from polomni.observatory.pipeline.events import EventLog, pipeline_event
from polomni.observatory.pipeline.sources.cosmology import (
    lambda_from_planck,
    load_planck_cosmo_params,
    load_planck_tt_power,
)
from polomni.observatory.pipeline.sources.gwosc import (
    GWCatalogSnapshot,
    GWEvent,
    fetch_gwtc_events,
    load_cached_gwtc,
    network_axis_from_detectors,
    new_events_since,
)
from polomni.observatory.reports.detection_report import save_json
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import DetectionReport, compute_rble_signature


@dataclass
class IngestResult:
    fetches: list[FetchResult] = field(default_factory=list)
    gw_snapshot: GWCatalogSnapshot | None = None
    gw_new_events: list = field(default_factory=list)


@dataclass
class PipelineResult:
    ran_at: datetime
    map_product_id: str
    map_path: Path
    nside_used: int
    detection: DetectionReport
    planck_lambda: float | None = None
    ingest: IngestResult = field(default_factory=IngestResult)
    report_path: Path | None = None
    power_spectrum_ell: np.ndarray | None = None
    power_spectrum_dl: np.ndarray | None = None
    gw_correlations: list[dict[str, Any]] = field(default_factory=list)


def calibrate_from_power_spectrum(
    cache: DataCache | None = None,
    *,
    product_id: str = "planck_cmb_tt_power",
) -> tuple[np.ndarray, np.ndarray]:
    """Load Planck TT power spectrum and return (ell, D_l) arrays."""
    cache = cache or DataCache()
    path = cache.resolved_path(product_id)
    if path is None:
        raise FileNotFoundError(f"Cached product not found: {product_id!r}")
    spectrum = load_planck_tt_power(path)
    return spectrum.ell, spectrum.dl


def correlate_gw_rble(
    preferred_axis: list[float] | np.ndarray,
    events: list[GWEvent],
    *,
    max_separation_deg: float = 30.0,
) -> list[dict[str, Any]]:
    """Stub: flag GW events whose detector-network axis lies near the RBLE axis."""
    import healpy as hp

    preferred = np.asarray(preferred_axis, dtype=float)
    preferred = preferred / (np.linalg.norm(preferred) + 1e-15)
    theta_p, phi_p = hp.vec2ang(preferred)
    dir_preferred = np.array([theta_p.item(), phi_p.item()])

    matches: list[dict[str, Any]] = []
    for event in events:
        axis: np.ndarray | None
        if event.network_axis is not None:
            axis = np.asarray(event.network_axis, dtype=float)
        else:
            axis = network_axis_from_detectors(event.detectors)
        if axis is None:
            continue

        axis = axis / (np.linalg.norm(axis) + 1e-15)
        theta_n, phi_n = hp.vec2ang(axis)
        dir_network = np.array([theta_n.item(), phi_n.item()])
        sep_deg = np.degrees(hp.rotator.angdist(dir_preferred, dir_network)).item()
        if sep_deg <= max_separation_deg:
            matches.append(
                {
                    "name": event.name,
                    "separation_deg": sep_deg,
                    "catalog": event.catalog,
                    "detectors": event.detectors,
                }
            )
    return matches


def ingest_standard_data(
    cache: DataCache | None = None,
    *,
    include_heavy: bool = False,
    force: bool = False,
    fetch_gw: bool = True,
    event_log: EventLog | None = None,
) -> IngestResult:
    """Fetch lite + standard catalog products and optionally GWOSC catalog."""
    cache = cache or DataCache()
    log = event_log or EventLog(cache.root / "events.jsonl")
    result = IngestResult()

    ids = list(STANDARD_FETCH_IDS)
    if include_heavy:
        ids.append("planck_smica_cmb")

    log.append(
        pipeline_event(
            "ingest_start",
            product_ids=ids,
            include_heavy=include_heavy,
            fetch_gw=fetch_gw,
        )
    )

    for pid in ids:
        fetch = fetch_product(get_product(pid), cache, force=force)
        result.fetches.append(fetch)
        log.append(
            pipeline_event(
                "ingest_fetch",
                product_id=pid,
                downloaded=fetch.downloaded,
                from_cache=fetch.from_cache,
                bytes_written=fetch.bytes_written,
            )
        )

    if fetch_gw:
        prev = load_cached_gwtc(cache)
        snap = fetch_gwtc_events(cache)
        result.gw_snapshot = snap
        result.gw_new_events = new_events_since(prev, snap)
        log.append(
            pipeline_event(
                "ingest_gw",
                results_count=snap.results_count,
                new_events=len(result.gw_new_events),
            )
        )

    log.append(pipeline_event("ingest_complete", fetch_count=len(result.fetches)))
    return result


def _resolve_map_product(map_product_id: str | None, include_heavy: bool) -> str:
    if map_product_id:
        return map_product_id
    if include_heavy:
        return "planck_smica_cmb"
    return "wmap_k_band"


def run_rble_pipeline(
    *,
    cache: DataCache | None = None,
    map_product_id: str | None = None,
    include_heavy: bool = False,
    force_fetch: bool = False,
    target_nside: int = 128,
    null_ensemble: int = 30,
    report_dir: Path | None = None,
    fetch_gw: bool = True,
    event_log: EventLog | None = None,
) -> PipelineResult:
    """Fetch real data, load CMB map, downsample, score RBLE signature."""
    cache = cache or DataCache()
    log = event_log or EventLog(cache.root / "events.jsonl")
    log.append(pipeline_event("pipeline_start", map_product_id=map_product_id))

    ingest = ingest_standard_data(
        cache,
        include_heavy=include_heavy or map_product_id == "planck_smica_cmb",
        force=force_fetch,
        fetch_gw=fetch_gw,
        event_log=log,
    )

    pid = _resolve_map_product(map_product_id, include_heavy)
    product = get_product(pid)
    fetch = fetch_product(product, cache, force=force_fetch)
    ingest.fetches.append(fetch)

    raw_map = load_healpix_map(fetch.path, field="T")
    cmb_map = downsample_map(raw_map, target_nside)

    log.append(
        pipeline_event(
            "score_start",
            map_product_id=pid,
            nside=target_nside,
            npix=int(cmb_map.size),
        )
    )

    detection = compute_rble_signature(cmb_map)
    null_maps = generate_null_ensemble(null_ensemble, target_nside, seed=7)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]
    mu = float(np.mean(null_scores))
    sigma = float(np.std(null_scores))
    if sigma > 0:
        detection.null_sigma = (detection.rble_score - mu) / sigma

    log.append(
        pipeline_event(
            "score_complete",
            rble_score=detection.rble_score,
            null_sigma=detection.null_sigma,
            preferred_axis=detection.preferred_axis,
        )
    )

    planck_lambda: float | None = None
    cosmo_path = cache.resolved_path("planck_lcdm_baseline")
    if cosmo_path:
        _ = load_planck_cosmo_params(cosmo_path)
    planck_lambda = lambda_from_planck(None)

    power_ell: np.ndarray | None = None
    power_dl: np.ndarray | None = None
    power_path = cache.resolved_path("planck_cmb_tt_power")
    if power_path:
        spectrum = load_planck_tt_power(power_path)
        power_ell, power_dl = spectrum.ell, spectrum.dl
    else:
        try:
            power_ell, power_dl = calibrate_from_power_spectrum(cache)
        except FileNotFoundError:
            power_ell, power_dl = None, None

    gw_events = ingest.gw_snapshot.events if ingest.gw_snapshot else []
    gw_correlations = correlate_gw_rble(detection.preferred_axis, gw_events)

    report_path: Path | None = None
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = report_dir / f"rble_{pid}_{ts}.json"
        save_json(detection, report_path)

    log.append(
        pipeline_event(
            "pipeline_complete",
            map_product_id=pid,
            gw_correlation_count=len(gw_correlations),
        )
    )

    return PipelineResult(
        ran_at=datetime.now(timezone.utc),
        map_product_id=pid,
        map_path=fetch.path,
        nside_used=target_nside,
        detection=detection,
        planck_lambda=planck_lambda,
        ingest=ingest,
        report_path=report_path,
        power_spectrum_ell=power_ell,
        power_spectrum_dl=power_dl,
        gw_correlations=gw_correlations,
    )


def list_cached_products(cache: DataCache | None = None) -> dict[str, Path | None]:
    cache = cache or DataCache()
    out: dict[str, Path | None] = {}
    for pid in CATALOG:
        out[pid] = cache.resolved_path(pid)
    out["gwtc_events"] = cache.resolved_path("gwtc_events")
    return out
