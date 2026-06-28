"""Coarse-to-fine hierarchical sky search for RBLE scar axes."""

from __future__ import annotations

import numpy as np

from polomni.observatory.ingest.healpix_loader import map_nside
from polomni.observatory.scoring.multiple_testing import count_sky_search_tests, passes_bonferroni
from polomni.observatory.scoring.rble_signature import DetectionReport, _radon_anisotropy_score, compute_rble_signature


def _axis_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


def _refine_axes_in_cone(
    center: np.ndarray,
    map_data: np.ndarray,
    *,
    cone_deg: float,
    n_samples: int,
) -> tuple[np.ndarray, float]:
    center = np.asarray(center, dtype=float)
    center = center / (np.linalg.norm(center) + 1e-15)
    best_axis = center
    best_score = -1.0
    cone_rad = np.radians(cone_deg)

    for _ in range(n_samples):
        perturb = np.random.randn(3)
        perturb -= perturb @ center * center
        if np.linalg.norm(perturb) < 1e-12:
            continue
        perturb = perturb / np.linalg.norm(perturb)
        angle = np.random.uniform(0, cone_rad)
        candidate = center * np.cos(angle) + perturb * np.sin(angle)
        candidate = candidate / (np.linalg.norm(candidate) + 1e-15)
        score = _radon_anisotropy_score(map_data, candidate)
        if score > best_score:
            best_score = score
            best_axis = candidate

    return best_axis, best_score


def _coarse_axis_healpix(
    map_data: np.ndarray,
    *,
    dir_nside: int = 8,
    n_eta: int = 24,
) -> tuple[np.ndarray, float]:
    """Coarse axis search on HEALPix pixel directions (geodesic Radon score)."""
    import healpy as hp

    from polomni.observatory.scoring.rble_signature import _radon_anisotropy_score

    theta, phi = hp.pix2ang(dir_nside, np.arange(hp.nside2npix(dir_nside)))
    directions = np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )
    best_score = -1.0
    best_axis = directions[0]
    for direction in directions:
        score = _radon_anisotropy_score(map_data, direction)
        if score > best_score:
            best_score = score
            best_axis = direction
    return best_axis, best_score


def hierarchical_sky_search(
    healpix_map: np.ndarray,
    *,
    coarse_nside: int = 16,
    refine_cone_deg: float = 15.0,
    refine_samples: int = 24,
    coarse_scan_angles: int = 12,
    seed: int = 0,
) -> DetectionReport:
    """Search for preferred RBLE axis with coarse downsample then local refinement."""
    rng = np.random.default_rng(seed)
    np.random.seed(int(rng.integers(0, 2**31 - 1)))

    full_map = np.asarray(healpix_map, dtype=float).ravel()
    current_nside = map_nside(full_map)

    dir_nside = min(8, max(4, current_nside // 2))
    coarse_axis, coarse_score = _coarse_axis_healpix(
        full_map,
        dir_nside=dir_nside,
        n_eta=24,
    )
    coarse = compute_rble_signature(full_map, coarse_axis, scan_angles=1)
    coarse = coarse.model_copy(
        update={"rble_score": coarse_score, "preferred_axis": coarse_axis.tolist()}
    )

    refine_axis, refine_score = _refine_axes_in_cone(
        coarse_axis,
        full_map,
        cone_deg=refine_cone_deg,
        n_samples=refine_samples,
    )

    final = compute_rble_signature(full_map, refine_axis, scan_angles=1)
    if refine_score > final.rble_score:
        final = final.model_copy(update={"rble_score": refine_score})

    dir_nside = min(8, coarse_nside // 2 or 8)
    import healpy as hp

    n_coarse = hp.nside2npix(dir_nside)
    n_tests = count_sky_search_tests(
        scan_angles=n_coarse,
        hierarchical_refine_samples=refine_samples,
    )
    if final.null_sigma > 0:
        bonf_pass, bonf_sigma, bonf_alpha = passes_bonferroni(final.null_sigma, n_tests)
    else:
        from polomni.observatory.scoring.multiple_testing import bonferroni_alpha

        bonf_pass = True
        bonf_sigma = 0.0
        bonf_alpha = bonferroni_alpha(0.05, n_tests)

    meta = dict(final.metadata)
    meta.update(
        {
            "search": "hierarchical",
            "coarse_nside": coarse_nside,
            "coarse_score": coarse.rble_score,
            "coarse_axis": coarse_axis.tolist(),
            "axis_shift_deg": _axis_separation_deg(coarse_axis, refine_axis),
            "refine_cone_deg": refine_cone_deg,
            "full_nside": current_nside,
            "bonferroni_n_tests": n_tests,
            "bonferroni_corrected_sigma": bonf_sigma,
            "bonferroni_alpha": bonf_alpha,
            "bonferroni_pass": bonf_pass,
        }
    )
    flags = dict(final.falsification_flags)
    flags["bonferroni"] = bonf_pass
    return final.model_copy(update={"metadata": meta, "falsification_flags": flags})
