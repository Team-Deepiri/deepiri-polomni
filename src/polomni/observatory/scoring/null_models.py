"""Null model tiers for P1 falsification (N0, N1, N2)."""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np

from polomni.observatory.ingest.healpix_loader import map_nside, synthetic_cmb_map
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import compute_rble_signature


class NullTier(str, Enum):
    GRF = "grf"
    CAMB_NOISE = "camb_noise"
    ROTATION_SHUFFLED = "rotation_shuffled"


def generate_grf_null(n_maps: int, nside: int, seed: int | None = None) -> np.ndarray:
    """N0: isotropic Gaussian CMB realizations."""
    return generate_null_ensemble(n_maps, nside, seed=seed)


def generate_camb_noise_null(
    n_maps: int,
    nside: int,
    seed: int | None = None,
    *,
    cache_root=None,
) -> np.ndarray:
    """N1: CAMB Cl + Gaussian draw when cache available; else GRF fallback."""
    rng = np.random.default_rng(seed)
    try:
        from polomni.observatory.pipeline.cache import DataCache
        from polomni.observatory.pipeline.processor import calibrate_from_power_spectrum

        cache = cache_root or DataCache()
        ell, dl = calibrate_from_power_spectrum(cache)
        maps = []
        for i in range(n_maps):
            m = synthetic_cmb_map(nside, seed=None if seed is None else seed + i)
            # Scale to match mean Cl amplitude proxy
            target_rms = float(np.sqrt(np.mean(dl[ell > 30])))
            scale = target_rms / (np.std(m) + 1e-12)
            maps.append(m * scale * (0.9 + 0.2 * rng.random()))
        return np.stack(maps, axis=0)
    except (FileNotFoundError, ImportError):
        return generate_grf_null(n_maps, nside, seed=seed)


def generate_rotation_shuffled_null(
    healpix_map: np.ndarray,
    n_maps: int,
    seed: int | None = None,
) -> np.ndarray:
    """N2: rotate map on S² (destroys axis structure, preserves value multiset)."""
    import healpy as hp

    base = np.asarray(healpix_map, dtype=float).ravel()
    nside = map_nside(base)
    rng = np.random.default_rng(seed)
    maps = []
    for _ in range(n_maps):
        rot = hp.Rotator(rot=(rng.uniform(0, 360), rng.uniform(0, 360), rng.uniform(0, 360)))
        maps.append(np.asarray(rot.rotate_map_pixel(base), dtype=float))
    return np.stack(maps, axis=0)


def te_correlation_along_axis(
    temperature_map: np.ndarray,
    axis: np.ndarray | list[float],
) -> float:
    """TE proxy: correlation of T with Q along scar axis great circle."""
    from polomni.observatory.ingest.polarization import extract_qu_maps

    t = np.asarray(temperature_map, dtype=float).ravel()
    q, _u = extract_qu_maps(t)
    axis_arr = np.asarray(axis, dtype=float)
    axis_arr = axis_arr / (np.linalg.norm(axis_arr) + 1e-15)
    try:
        import healpy as hp

        nside = hp.get_nside(t)
        theta, phi = hp.pix2ang(nside, np.arange(t.size))
        x = np.column_stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
        )
        ring = np.abs(x @ axis_arr) > 0.85
        if ring.sum() < 20:
            return 0.0
        t_ring = t[ring]
        q_ring = q[ring]
        if np.std(t_ring) < 1e-12 or np.std(q_ring) < 1e-12:
            return 0.0
        return float(np.corrcoef(t_ring, q_ring)[0, 1])
    except ImportError:
        return 0.0


def _tier_maps(
    tier: NullTier,
    reference_map: np.ndarray,
    n_maps: int,
    nside: int,
    seed: int,
) -> np.ndarray:
    if tier == NullTier.GRF:
        return generate_grf_null(n_maps, nside, seed=seed)
    if tier == NullTier.CAMB_NOISE:
        return generate_camb_noise_null(n_maps, nside, seed=seed)
    return generate_rotation_shuffled_null(reference_map, n_maps, seed=seed)


def run_null_tier_comparison(
    healpix_map: np.ndarray,
    tiers: list[NullTier | str] | None = None,
    *,
    n_ensemble: int = 30,
    seed: int = 7,
    n_hat: np.ndarray | list[float] | None = None,
) -> dict[str, Any]:
    """Score map vs each null tier; return per-tier mu, sigma, p-value, sigma."""
    from polomni.observatory.scoring.multiple_testing import sigma_to_two_sided_p

    tiers = tiers or [NullTier.GRF, NullTier.CAMB_NOISE, NullTier.ROTATION_SHUFFLED]
    cmap = np.asarray(healpix_map, dtype=float).ravel()
    nside = map_nside(cmap)

    if n_hat is not None:
        detection = compute_rble_signature(cmap, n_hat, scan_angles=1)
    else:
        detection = compute_rble_signature(cmap)

    score = detection.rble_score
    out: dict[str, Any] = {
        "score": score,
        "preferred_axis": detection.preferred_axis,
        "te_correlation": te_correlation_along_axis(cmap, detection.preferred_axis),
        "tiers": {},
    }

    for tier in tiers:
        t = NullTier(tier) if isinstance(tier, str) else tier
        null_maps = _tier_maps(t, cmap, n_ensemble, nside, seed)
        null_scores = [
            compute_rble_signature(m, detection.preferred_axis, scan_angles=1).rble_score
            for m in null_maps
        ]
        mu = float(np.mean(null_scores))
        sigma = float(np.std(null_scores))
        raw_sigma = (score - mu) / (sigma + 1e-12)
        p_value = sigma_to_two_sided_p(abs(raw_sigma))
        out["tiers"][t.value] = {
            "mu": mu,
            "sigma": sigma,
            "raw_sigma": raw_sigma,
            "p_value": p_value,
            "n_ensemble": n_ensemble,
        }
    return out
