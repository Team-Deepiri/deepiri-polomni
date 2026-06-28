"""Geodesic Radon transform on S^2 for CMB scars (RBLE Eq. 6)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

_HEALPY_AVAILABLE = False
try:
    import healpy as hp  # type: ignore[import-untyped]

    _HEALPY_AVAILABLE = True
except ImportError:
    hp = None  # type: ignore[assignment]


def _unit_vector_on_sphere(n_hat: NDArray[np.floating]) -> NDArray[np.float64]:
    v = np.asarray(n_hat, dtype=np.float64).ravel()
    if v.size != 3:
        raise ValueError("n_hat must be a 3-vector")
    norm = np.linalg.norm(v)
    if norm < 1e-15:
        raise ValueError("n_hat must be non-zero")
    return v / norm


def _great_circle_points(
    n_hat: NDArray[np.floating],
    n_samples: int = 360,
) -> NDArray[np.float64]:
    """Sample unit vectors along the great circle with normal n_hat."""
    n = _unit_vector_on_sphere(n_hat)
    ref = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    if abs(np.dot(n, ref)) > 0.95:
        ref = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    u = np.cross(n, ref)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    t = np.linspace(0.0, 2.0 * np.pi, n_samples, endpoint=False)
    return np.cos(t)[:, None] * u + np.sin(t)[:, None] * v


def _fallback_radon_s2(
    healpix_map: NDArray[np.floating],
    n_hat: NDArray[np.floating],
    eta: float,
    nside: int,
) -> float:
    """Chord integration along a great circle using synthetic HEALPix-like indexing."""
    n_pix = 12 * nside * nside
    if healpix_map.size != n_pix:
        raise ValueError(f"healpix_map length {healpix_map.size} != 12*nside^2={n_pix}")

    circle = _great_circle_points(n_hat)
    theta = np.arccos(np.clip(circle[:, 2], -1.0, 1.0))
    phi = np.mod(np.arctan2(circle[:, 1], circle[:, 0]), 2.0 * np.pi)

    # Equirectangular proxy index for fallback (not exact HEALPix nesting).
    ipix = (
        (theta / np.pi * (2 * nside)).astype(int) * (4 * nside)
        + (phi / (2.0 * np.pi) * (4 * nside)).astype(int)
    ) % n_pix

    arc_length = 2.0 * np.pi * np.sin(np.arccos(np.clip(abs(n_hat[2]), 0.0, 1.0)))
    if arc_length < 1e-12:
        arc_length = 2.0 * np.pi

    shifted = np.roll(healpix_map.ravel(), int(eta * n_pix / (2.0 * np.pi)))
    samples = shifted[ipix]
    return float(np.sum(samples) * arc_length / len(samples))


def radon_transform_s2(
    healpix_map: NDArray[np.floating],
    n_hat: NDArray[np.floating],
    eta: float,
    *,
    nside: int | None = None,
) -> float:
    """Geodesic line integral R_S2[f](n_hat, eta) along great circle normal to n_hat.

    Uses healpy pixel interpolation when available; otherwise a numpy great-circle
    quadrature with equirectangular indexing.
    """
    m = np.asarray(healpix_map, dtype=np.float64).ravel()
    if m.size == 0:
        raise ValueError("healpix_map must be non-empty")

    if nside is None:
        nside = int(np.sqrt(m.size / 12.0))
        if 12 * nside * nside != m.size:
            raise ValueError("Cannot infer nside; pass nside explicitly")

    n = _unit_vector_on_sphere(n_hat)

    if _HEALPY_AVAILABLE and hp is not None:
        circle = _great_circle_points(n, n_samples=720)
        theta = np.arccos(np.clip(circle[:, 2], -1.0, 1.0))
        phi = np.mod(np.arctan2(circle[:, 1], circle[:, 0]), 2.0 * np.pi)
        # Shift along circle by eta (arc-length parameter).
        phi_shifted = np.mod(phi + eta, 2.0 * np.pi)
        values = hp.get_interp_val(m, theta, phi_shifted)
        arc_element = 2.0 * np.pi / len(values)
        return float(np.sum(values) * arc_element)

    return _fallback_radon_s2(m, n, eta, nside)
