"""RBLE scar signature S_RBLE(n̂) on HEALPix maps (Eq. 6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from polomni.observatory.scoring.radon_tomography import (
    DEFAULT_W_PARAMS,
    build_radon_tomogram,
    rble_score_at_axis,
)


class DetectionReport(BaseModel):
    """Observatory detection report for Radon-bifurcated landscape scars."""

    rble_score: float = Field(description="Peak S_RBLE signature strength.")
    preferred_axis: list[float] = Field(description="Unit vector n̂ of preferred scar axis.")
    n_hat: list[float] = Field(description="View axis used for scoring.")
    fnl_proxy: float = Field(default=0.0, description="Local non-Gaussianity proxy (f_NL).")
    null_sigma: float = Field(default=0.0, description="Significance vs null ensemble (σ).")
    falsification_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def compute_fnl_proxy(map_data: np.ndarray) -> float:
    """Estimate a proxy for local non-Gaussianity f_NL via temperature field skewness."""
    if map_data.size == 0:
        return 0.0
    mean = np.mean(map_data)
    std = np.std(map_data)
    if std == 0:
        return 0.0

    skewness = np.mean(((map_data - mean) / std) ** 3)
    return float(skewness)


def _axis_from_angles(theta: float, phi: float) -> np.ndarray:
    return np.array(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)],
        dtype=float,
    )


def _radon_anisotropy_score(map_data: np.ndarray, n_hat: np.ndarray) -> float:
    """Fast axis-aligned anisotropy proxy for coarse sky search (not Eq. 6 integral)."""
    n_hat = np.asarray(n_hat, dtype=float)
    n_hat = n_hat / (np.linalg.norm(n_hat) + 1e-15)
    try:
        import healpy as hp

        nside = hp.get_nside(map_data)
        theta, phi = hp.pix2ang(nside, np.arange(map_data.size))
        x = np.column_stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
        )
        mu = x @ n_hat
        parallel = map_data[np.abs(mu) > 0.9]
        orthogonal = map_data[np.abs(mu) < 0.3]
        if parallel.size < 10 or orthogonal.size < 10:
            return 0.0
        return float(np.std(parallel) / (np.std(orthogonal) + 1e-12))
    except ImportError:
        phase = np.arange(map_data.size) * n_hat[0]
        high = map_data[np.cos(phase) > 0.8]
        low = map_data[np.cos(phase) < 0.2]
        if high.size < 10 or low.size < 10:
            return 0.0
        return float(np.std(high) / (np.std(low) + 1e-12))


def _score_at_axis(
    healpix_map: np.ndarray,
    axis: np.ndarray,
    *,
    n_eta: int,
    score_weight: Literal["integral", "bifurcation", "contrast"],
) -> float:
    return rble_score_at_axis(
        healpix_map,
        axis,
        weight=score_weight,
        n_eta=n_eta,
        apply_string_filter=True,
        W_params=DEFAULT_W_PARAMS,
        method="transform",
    )


def compute_rble_signature(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
    *,
    scan_angles: int = 36,
    score_weight: Literal["integral", "bifurcation", "contrast"] = "integral",
    search_n_eta: int = 32,
    report_n_eta: int = 128,
    n_null: int = 0,
    null_seed: int | None = None,
    family_alpha: float = 0.05,
) -> DetectionReport:
    """Compute RBLE scar signature via geodesic Radon tomography (Eq. 6).

    When ``n_null > 0``, fills ``null_sigma`` and Bonferroni metadata from
    ``SNR = (S − μ_null) / σ_null`` at the preferred axis. Without nulls,
    Bonferroni is left unset (score alone is not Gaussian σ).
    """
    from polomni.observatory.ingest.healpix_loader import map_nside
    from polomni.observatory.scoring.multiple_testing import count_sky_search_tests
    from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
    from polomni.observatory.scoring.snr import attach_null_significance

    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    map_rms = float(np.std(healpix_map))

    fnl_val = compute_fnl_proxy(healpix_map)

    if n_hat is not None:
        axis = np.asarray(n_hat, dtype=float)
        axis = axis / (np.linalg.norm(axis) + 1e-15)
        score = _score_at_axis(healpix_map, axis, n_eta=report_n_eta, score_weight=score_weight)
        preferred = axis
        tomogram = build_radon_tomogram(
            healpix_map,
            axis,
            n_eta=report_n_eta,
            method="transform",
        )
        n_tests = 1
    else:
        best_score = -1.0
        preferred = np.array([0.0, 0.0, 1.0])
        thetas = np.linspace(0.2, np.pi - 0.2, scan_angles)
        phis = np.linspace(0, 2 * np.pi, scan_angles, endpoint=False)
        for theta in thetas:
            for phi in phis:
                axis = _axis_from_angles(theta, phi)
                score = _score_at_axis(
                    healpix_map,
                    axis,
                    n_eta=search_n_eta,
                    score_weight=score_weight,
                )
                if score > best_score:
                    best_score = score
                    preferred = axis
        score = best_score
        tomogram = build_radon_tomogram(
            healpix_map,
            preferred,
            n_eta=report_n_eta,
            method="transform",
        )
        n_tests = count_sky_search_tests(scan_angles=scan_angles * scan_angles)

    flags = {
        "radon_anisotropic": score > 0.25,
        "te_coupling_stub": map_rms > 0.0,
        "null_rejected_stub": score > 0.5,
        "geodesic_radon": True,
        "null_significance_computed": False,
    }
    meta = {
        "map_rms": map_rms,
        "npix": int(healpix_map.size),
        "score_method": "geodesic_radon_integral",
        "score_weight": score_weight,
        "tomogram_integral": tomogram.score_integral,
        "tomogram_bifurcation": tomogram.score_bifurcation,
        "tomogram_contrast": tomogram.score_contrast,
    }

    null_sigma = 0.0
    if n_null > 0:
        nside = map_nside(healpix_map)
        seed = 0 if null_seed is None else int(null_seed)
        null_maps = generate_null_ensemble(n_null, nside, seed=seed)
        null_scores = [
            _score_at_axis(m, preferred, n_eta=max(search_n_eta, 24), score_weight=score_weight)
            for m in null_maps
        ]
        sig = attach_null_significance(
            float(score),
            null_scores,
            n_tests=n_tests,
            family_alpha=family_alpha,
        )
        null_sigma = float(sig["null_sigma"])
        flags["null_significance_computed"] = True
        flags["bonferroni"] = bool(sig["bonferroni_pass"])
        meta.update(
            {
                "bonferroni_pass": bool(sig["bonferroni_pass"]),
                "bonferroni_corrected_sigma": float(sig["bonferroni_corrected_sigma"]),
                "bonferroni_alpha": float(sig["bonferroni_alpha"]),
                "bonferroni_n_tests": int(n_tests),
                "bonferroni_status": "computed_known_axis_null",
                "snr": float(sig["snr"]),
                "mu_null": float(sig["mu_null"]),
                "sigma_null_std": float(sig["sigma_null"]),
                "p_value": float(sig["p_value"]),
                "n_null": int(n_null),
            }
        )

    return DetectionReport(
        rble_score=float(score),
        preferred_axis=preferred.tolist(),
        n_hat=preferred.tolist(),
        null_sigma=null_sigma,
        fnl_proxy=fnl_val,
        falsification_flags=flags,
        metadata=meta,
    )


def inject_synthetic_scar(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    amplitude: float = 5.0,
) -> np.ndarray:
    """Inject axis-aligned scar for Gate 2 calibration (anisotropy search target)."""
    n_hat = np.asarray(n_hat, dtype=float)
    n_hat = n_hat / (np.linalg.norm(n_hat) + 1e-15)
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    try:
        import healpy as hp

        nside = hp.get_nside(healpix_map)
        theta, phi = hp.pix2ang(nside, np.arange(healpix_map.size))
        x = np.column_stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
        )
        alignment = np.abs(x @ n_hat)
        ring = np.exp(-((1.0 - alignment) ** 2) / 0.005)
        tangent = np.cross(n_hat, np.array([0.0, 0.0, 1.0]))
        if np.linalg.norm(tangent) < 1e-8:
            tangent = np.cross(n_hat, np.array([0.0, 1.0, 0.0]))
        tangent /= np.linalg.norm(tangent) + 1e-15
        bitangent = np.cross(n_hat, tangent)
        phase = np.arctan2(x @ bitangent, x @ tangent)
        geodesic_mod = 1.0 + 0.6 * np.sin(4.0 * phase)
        pole = alignment**6
        scar = amplitude * (0.7 * ring * geodesic_mod + 0.3 * pole)
    except ImportError:
        phase = np.arange(healpix_map.size) / healpix_map.size
        scar = amplitude * np.exp(-((phase - 0.5) ** 2) / 0.01)
    return healpix_map + scar
