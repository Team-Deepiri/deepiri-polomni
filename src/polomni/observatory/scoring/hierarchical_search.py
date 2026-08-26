"""Coarse-to-fine hierarchical sky search for RBLE scar axes."""

from __future__ import annotations

import healpy as hp
import numpy as np

from polomni.observatory.ingest.healpix_loader import map_nside
from polomni.observatory.scoring.axis_search import PreparedCmbMap, search_best_axis
from polomni.observatory.scoring.multiple_testing import (
    bonferroni_alpha,
    count_sky_search_tests,
)
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.radon_tomography import build_radon_tomogram, rble_score_at_axis
from polomni.observatory.scoring.rble_signature import DetectionReport
from polomni.observatory.scoring.snr import attach_null_significance


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
    n_null: int = 0,
    null_seed: int | None = None,
    family_alpha: float = 0.05,
    neural_prescreen: bool = False,
) -> DetectionReport:
    """Search for preferred RBLE axis — one filter pass, pixel Radon throughout.

    When ``neural_prescreen`` is True and a scar-classifier checkpoint exists,
    the neural axis seeds the refine cone (does not replace the search).
    """
    full_map = np.asarray(healpix_map, dtype=float).ravel()
    current_nside = map_nside(full_map)
    prepared = PreparedCmbMap.from_map(full_map)

    neural_seed_axis = None
    if neural_prescreen:
        try:
            from polomni.neural.scar_classifier.rble_scanner import predict_preferred_axis

            neural_seed_axis = predict_preferred_axis(full_map)
        except Exception:
            neural_seed_axis = None

    dir_nside = min(8, max(4, current_nside // 4))
    refine_axis, refine_score, search_meta = search_best_axis(
        prepared,
        dir_nside=dir_nside,
        refine_cone_deg=refine_cone_deg,
        refine_samples=max(refine_samples, coarse_scan_angles),
        search_n_eta=search_n_eta,
        seed=seed,
        seed_axis=neural_seed_axis,
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

    null_sigma = 0.0
    bonf_pass = False
    bonf_sigma = 0.0
    bonf_alpha = bonferroni_alpha(family_alpha, n_tests)
    bonf_status = "inconclusive_no_nulls"
    snr_meta: dict[str, float | int | bool] = {}

    if n_null > 0:
        nseed = seed + 17 if null_seed is None else int(null_seed)
        null_maps = generate_null_ensemble(n_null, current_nside, seed=nseed)
        null_scores = np.asarray(
            [
                rble_score_at_axis(
                    m,
                    refine_axis,
                    n_eta=max(search_n_eta, 24),
                    apply_string_filter=True,
                    method="pixel",
                )
                for m in null_maps
            ],
            dtype=float,
        )
        s_at_axis = float(
            rble_score_at_axis(
                prepared.filtered,
                refine_axis,
                n_eta=max(search_n_eta, 24),
                apply_string_filter=False,
                method="pixel",
            )
        )
        sig = attach_null_significance(
            s_at_axis,
            null_scores,
            n_tests=n_tests,
            family_alpha=family_alpha,
        )
        null_sigma = float(sig["null_sigma"])
        bonf_pass = bool(sig["bonferroni_pass"])
        bonf_sigma = float(sig["bonferroni_corrected_sigma"])
        bonf_alpha = float(sig["bonferroni_alpha"])
        bonf_status = "computed_known_axis_null"
        snr_meta = {
            "snr": float(sig["snr"]),
            "mu_null": float(sig["mu_null"]),
            "sigma_null_std": float(sig["sigma_null"]),
            "p_value": float(sig["p_value"]),
            "s_at_preferred_axis": s_at_axis,
            "n_null": int(n_null),
        }

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
        "bonferroni_status": bonf_status,
        **snr_meta,
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
        "null_significance_computed": n_null > 0,
    }

    return DetectionReport(
        rble_score=float(final_score),
        preferred_axis=refine_axis.tolist(),
        n_hat=refine_axis.tolist(),
        null_sigma=float(null_sigma),
        falsification_flags=flags,
        metadata=meta,
    )
