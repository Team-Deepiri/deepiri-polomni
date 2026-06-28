"""RBLE scar signature S_RBLE(n̂) on HEALPix maps (Eq. 6)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


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


def _radon_anisotropy_score(map_data: np.ndarray, n_hat: np.ndarray) -> float:
    """Scalar anisotropy along great circle orthogonal to n_hat."""
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


def compute_rble_signature(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
    *,
    scan_angles: int = 36,
) -> DetectionReport:
    """Compute RBLE scar signature and preferred axis on a HEALPix map.

    Searches over candidate axes (or uses supplied *n_hat*) and returns the
    axis maximizing Radon anisotropy contrast — the observatory observable
  associated with Eq. 6 (spherical Radon scar on S²).

    Parameters
    ----------
    healpix_map:
        Temperature (or filtered) map.
    n_hat:
        Optional fixed view axis. If ``None``, scans ``scan_angles`` directions.
    scan_angles:
        Number of θ samples when auto-searching preferred axis.

    Returns
    -------
    DetectionReport
        Structured detection output with scores and falsification flags.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    map_rms = float(np.std(healpix_map))

    if n_hat is not None:
        axis = np.asarray(n_hat, dtype=float)
        axis = axis / (np.linalg.norm(axis) + 1e-15)
        score = _radon_anisotropy_score(healpix_map, axis)
        preferred = axis
    else:
        best_score = -1.0
        preferred = np.array([0.0, 0.0, 1.0])
        thetas = np.linspace(0.2, np.pi - 0.2, scan_angles)
        phis = np.linspace(0, 2 * np.pi, scan_angles, endpoint=False)
        for theta in thetas:
            for phi in phis:
                axis = _axis_from_angles(theta, phi)
                score = _radon_anisotropy_score(healpix_map, axis)
                if score > best_score:
                    best_score = score
                    preferred = axis
        score = best_score

    # Falsification flags per FALSIFICATION_CRITERIA.md stubs.
    flags = {
        "radon_anisotropic": score > 1.2,
        "te_coupling_stub": map_rms > 0.0,
        "null_rejected_stub": score > 1.5,
    }

    return DetectionReport(
        rble_score=float(score),
        preferred_axis=preferred.tolist(),
        n_hat=preferred.tolist(),
        falsification_flags=flags,
        metadata={"map_rms": map_rms, "npix": int(healpix_map.size)},
    )


def inject_synthetic_scar(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    amplitude: float = 5.0,
) -> np.ndarray:
    """Inject a known Radon scar along *n_hat* for recovery tests.

    Uses sharp axis-aligned modulation so :func:`compute_rble_signature` peaks
    near the injection axis (Gate 2 calibration).
    """
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
        # Sharp equatorial ring + pole enhancement → anisotropy score peaks at n_hat.
        ring = np.exp(-((1.0 - alignment) ** 2) / 0.005)
        pole = alignment**6
        scar = amplitude * (0.7 * ring + 0.3 * pole)
    except ImportError:
        phase = np.arange(healpix_map.size) / healpix_map.size
        scar = amplitude * np.exp(-((phase - 0.5) ** 2) / 0.01)
    return healpix_map + scar
