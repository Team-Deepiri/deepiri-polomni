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
    null_sigma: float = Field(default=0.0, description="Significance vs null ensemble (σ).")
    falsification_flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _axis_from_angles(theta: float, phi: float) -> np.ndarray:
    return np.array(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)],
        dtype=float,
    )


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
) -> DetectionReport:
    """Compute RBLE scar signature via geodesic Radon tomography (Eq. 6).

    Uses the string-filtered geodesic line integral
    S_RBLE(n̂) = ∫ |R_{S²}[T ⊗ W_string](n̂, η)| dη
    from ``radon_tomography.py``, not a pixel anisotropy proxy.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    map_rms = float(np.std(healpix_map))

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

    flags = {
        "radon_anisotropic": score > 0.25,
        "te_coupling_stub": map_rms > 0.0,
        "null_rejected_stub": score > 0.5,
        "geodesic_radon": True,
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

    return DetectionReport(
        rble_score=float(score),
        preferred_axis=preferred.tolist(),
        n_hat=preferred.tolist(),
        falsification_flags=flags,
        metadata=meta,
    )


def inject_synthetic_scar(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    amplitude: float = 5.0,
) -> np.ndarray:
    """Inject a geodesic Radon scar modulated along arcs normal to *n_hat*."""
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
        scar = amplitude * (0.5 * ring * geodesic_mod + 0.3 * pole)
    except ImportError:
        phase = np.arange(healpix_map.size) / healpix_map.size
        scar = amplitude * np.exp(-((phase - 0.5) ** 2) / 0.01)
    return healpix_map + scar
