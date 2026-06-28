"""Cosmos analytics — axis profiles, null histograms, dual-map comparison."""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import compute_rble_signature
from polomni.observatory.studies.config import load_p1_config
from polomni.observatory.studies.gates import load_latest_result
from polomni.viz.cosmos.helpers import axis_lonlat, great_circle_ring, load_real_sky_map

_SKY_CACHE: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 300.0


def _subsample_sky(
    cmb: np.ndarray,
    nside: int,
    *,
    max_pixels: int = 6000,
) -> tuple[list[float], list[float], list[float]]:
    import healpy as hp

    theta, phi = hp.pix2ang(nside, np.arange(cmb.size))
    lon = np.degrees(phi)
    lat = 90.0 - np.degrees(theta)
    if cmb.size > max_pixels:
        step = max(1, cmb.size // max_pixels)
        idx = np.arange(0, cmb.size, step)
        return lon[idx].tolist(), lat[idx].tolist(), cmb[idx].tolist()
    return lon.tolist(), lat.tolist(), cmb.tolist()


def sky_payload_cached(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    max_pixels: int = 8000,
    force: bool = False,
) -> dict[str, Any]:
    """Cached real-sky payload (hierarchical search is expensive)."""
    key = (map_product_id, nside)
    now = time.monotonic()
    if not force and key in _SKY_CACHE:
        expiry, payload = _SKY_CACHE[key]
        if now < expiry:
            return payload

    cmb, pid, path = load_real_sky_map(map_product_id=map_product_id, nside=nside)
    detection = hierarchical_sky_search(
        cmb,
        coarse_nside=min(16, nside // 4 or 16),
        seed=0,
    )
    axis = np.asarray(detection.preferred_axis, dtype=float)
    lon, lat, vals = _subsample_sky(cmb, nside, max_pixels=max_pixels)
    axis_lon, axis_lat = axis_lonlat(axis)
    ring_lon, ring_lat = great_circle_ring(axis)

    payload = {
        "map_product_id": pid,
        "map_path": str(path) if path else None,
        "nside": nside,
        "lon": lon,
        "lat": lat,
        "values": vals,
        "rble_score": float(detection.rble_score),
        "null_sigma": float(detection.null_sigma),
        "preferred_axis": axis.tolist(),
        "axis_marker": {"lon": axis_lon, "lat": axis_lat},
        "scar_ring": {"lon": ring_lon, "lat": ring_lat},
        "metadata": detection.metadata,
    }
    _SKY_CACHE[key] = (now + _CACHE_TTL_SEC, payload)
    return payload


def axis_radial_profile(
    healpix_map: np.ndarray,
    axis: np.ndarray | list[float],
    *,
    n_bins: int = 36,
) -> dict[str, Any]:
    """Binned |T| and RMS vs polar angle from preferred axis (degrees)."""
    import healpy as hp

    cmap = np.asarray(healpix_map, dtype=float).ravel()
    axis_arr = np.asarray(axis, dtype=float)
    axis_arr = axis_arr / (np.linalg.norm(axis_arr) + 1e-15)
    nside = hp.get_nside(cmap)
    theta, phi = hp.pix2ang(nside, np.arange(cmap.size))
    x = np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )
    mu = np.clip(x @ axis_arr, -1.0, 1.0)
    angle_deg = np.degrees(np.arccos(np.abs(mu)))

    edges = np.linspace(0.0, 90.0, n_bins + 1)
    centers: list[float] = []
    mean_abs: list[float] = []
    rms: list[float] = []
    counts: list[int] = []
    for i in range(n_bins):
        mask = (angle_deg >= edges[i]) & (angle_deg < edges[i + 1])
        if mask.sum() < 5:
            centers.append(float(0.5 * (edges[i] + edges[i + 1])))
            mean_abs.append(0.0)
            rms.append(0.0)
            counts.append(0)
            continue
        vals = cmap[mask]
        centers.append(float(0.5 * (edges[i] + edges[i + 1])))
        mean_abs.append(float(np.mean(np.abs(vals))))
        rms.append(float(np.std(vals)))
        counts.append(int(mask.sum()))

    return {
        "angle_deg": centers,
        "mean_abs_t": mean_abs,
        "rms_t": rms,
        "counts": counts,
        "n_bins": n_bins,
    }


def null_score_histogram(
    healpix_map: np.ndarray,
    *,
    n_ensemble: int = 40,
    seed: int = 7,
    n_bins: int = 20,
) -> dict[str, Any]:
    """Null ensemble score distribution vs observed RBLE score."""
    import healpy as hp

    cmap = np.asarray(healpix_map, dtype=float).ravel()
    nside = hp.get_nside(cmap)
    detection = compute_rble_signature(cmap)
    observed = float(detection.rble_score)
    axis = np.asarray(detection.preferred_axis, dtype=float)

    null_maps = generate_null_ensemble(n_ensemble, nside, seed=seed)
    null_scores = [
        float(compute_rble_signature(m, axis, scan_angles=1).rble_score) for m in null_maps
    ]
    mu = float(np.mean(null_scores))
    sigma = float(np.std(null_scores))
    raw_sigma = (observed - mu) / (sigma + 1e-12)

    lo = min(null_scores + [observed]) - 0.05
    hi = max(null_scores + [observed]) + 0.05
    counts, edges = np.histogram(null_scores, bins=n_bins, range=(lo, hi))
    centers = 0.5 * (edges[:-1] + edges[1:])

    return {
        "observed_score": observed,
        "null_mu": mu,
        "null_sigma": sigma,
        "raw_sigma": raw_sigma,
        "null_scores": null_scores,
        "histogram": {
            "bin_centers": centers.tolist(),
            "counts": counts.tolist(),
            "edges": edges.tolist(),
        },
        "n_ensemble": n_ensemble,
    }


def dual_map_comparison(*, nside: int = 64) -> dict[str, Any]:
    """Calibration (WMAP) vs holdout (Planck) side-by-side scores and sky snippets."""
    config = load_p1_config()
    cal_id = str(config.maps.get("calibration_product_id", "wmap_k_band"))
    hold_id = str(config.maps.get("holdout_product_id", "planck_smica_cmb"))

    cal_sky = sky_payload_cached(map_product_id=cal_id, nside=nside, max_pixels=5000)
    hold_sky = sky_payload_cached(map_product_id=hold_id, nside=nside, max_pixels=5000)

    cal_cmb, _, _ = load_real_sky_map(map_product_id=cal_id, nside=nside)
    hold_cmb, _, _ = load_real_sky_map(map_product_id=hold_id, nside=nside)

    cal_profile = axis_radial_profile(cal_cmb, cal_sky["preferred_axis"])
    hold_profile = axis_radial_profile(hold_cmb, hold_sky["preferred_axis"])

    result = load_latest_result()
    return {
        "calibration": {
            "product_id": cal_id,
            "sky": cal_sky,
            "axis_profile": cal_profile,
        },
        "holdout": {
            "product_id": hold_id,
            "sky": hold_sky,
            "axis_profile": hold_profile,
        },
        "study_result": result,
        "verdict": {
            "calibration_stronger": cal_sky["rble_score"] > hold_sky["rble_score"],
            "score_delta": float(cal_sky["rble_score"] - hold_sky["rble_score"]),
            "p1_supported": bool(result.get("p1_supported")) if result else None,
            "p1_falsified": bool(result.get("p1_falsified")) if result else None,
        },
    }
