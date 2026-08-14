"""Coarse-to-fine hierarchical sky search for RBLE scar axes."""

from __future__ import annotations

import numpy as np
import healpy as hp
from polomni.observatory.ingest.healpix_loader import map_nside
from polomni.observatory.scoring.axis_search import PreparedCmbMap, search_best_axis
from polomni.observatory.scoring.multiple_testing import (
    count_sky_search_tests,
    passes_bonferroni,
)
from polomni.observatory.scoring.radon_tomography import build_radon_tomogram
from polomni.observatory.scoring.rble_signature import DetectionReport


def _axis_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


def hierarchical_sky_search(
    healpix_map: np.ndarray,
    *,
    coarse_nside: int = 16,
    refine_cone_deg: float = 12.0,
    refine_samples: int = 16,
    coarse_scan_angles: int = 12,
    seed: int = 0,
    search_n_eta: int = 16,
    report_n_eta: int = 48,
    full_tomogram: bool = True,
) -> DetectionReport:
    """Search for preferred RBLE axis — one filter pass, pixel Radon throughout."""
    full_map = np.asarray(healpix_map, dtype=float).ravel()
    current_nside = map_nside(full_map)
    prepared = PreparedCmbMap.from_map(full_map)

    dir_nside = min(8, max(4, current_nside // 4))
    refine_axis, refine_score, search_meta = search_best_axis(
        prepared,
        dir_nside=dir_nside,
        refine_cone_deg=refine_cone_deg,
        refine_samples=max(refine_samples, coarse_scan_angles),
        search_n_eta=search_n_eta,
        seed=seed,
    )

    if full_tomogram:
        tomogram = build_radon_tomogram(
            prepared.raw,
            refine_axis,
            n_eta=report_n_eta,
            method="pixel",
        )
        final_score = max(refine_score, tomogram.score_integral)
        tomogram_meta = {
            "tomogram_integral": tomogram.score_integral,
            "tomogram_bifurcation": tomogram.score_bifurcation,
        }
    else:
        final_score = refine_score
        tomogram_meta = {"tomogram_integral": refine_score, "tomogram_bifurcation": 0.0}

    n_coarse = hp.nside2npix(dir_nside)
    n_tests = count_sky_search_tests(
        scan_angles=n_coarse,
        hierarchical_refine_samples=refine_samples,
    )

    bonf_pass, bonf_sigma, bonf_alpha = passes_bonferroni(
        raw_sigma=final_score,
        n_tests=n_tests,
        alpha=0.05,
    )

    meta = {
        "search": "hierarchical",
        "coarse_nside": coarse_nside,
        "full_nside": current_nside,
        "refine_cone_deg": refine_cone_deg,
        "report_n_eta": report_n_eta,
        "score_method": "pixel_radon_cached_filter",
        **tomogram_meta,
        "bonferroni_n_tests": n_tests,
        "bonferroni_corrected_sigma": bonf_sigma,
        "bonferroni_alpha": bonf_alpha,
        "bonferroni_pass": bonf_pass,
        **search_meta,
    }
    if "coarse_axis" in search_meta:
        meta["axis_shift_deg"] = _axis_separation_deg(
            np.asarray(search_meta["coarse_axis"]),
            refine_axis,
        )

    flags = {
        "radon_anisotropic": final_score > 0.25,
        "geodesic_radon": True,
        "bonferroni": bonf_pass,
    }

    return DetectionReport(
        rble_score=float(final_score),
        preferred_axis=refine_axis.tolist(),
        n_hat=refine_axis.tolist(),
        falsification_flags=flags,
        metadata=meta,
    )
