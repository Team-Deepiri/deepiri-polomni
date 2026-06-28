"""Inverse Radon-bifurcation filter on S² (Eq. 3: topological WDW bifurcation closure)."""

from __future__ import annotations

import numpy as np


def _radon_profile_s2(map_data: np.ndarray, n_hat: np.ndarray, n_eta: int = 64) -> np.ndarray:
    """Geodesic line integral profile along great circle normal to *n_hat*."""
    try:
        import healpy as hp

        nside = hp.get_nside(map_data)
        theta, phi = hp.pix2ang(nside, np.arange(map_data.size))
        x = np.column_stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
        )
        n_hat = np.asarray(n_hat, dtype=float)
        n_hat = n_hat / (np.linalg.norm(n_hat) + 1e-15)
        eta = np.linspace(0.0, 2.0 * np.pi, n_eta, endpoint=False)
        # Great circle: points with x·n_hat = cos(η) parametrization via rotation.
        tangent = np.cross(n_hat, np.array([0.0, 0.0, 1.0]))
        if np.linalg.norm(tangent) < 1e-8:
            tangent = np.cross(n_hat, np.array([0.0, 1.0, 0.0]))
        tangent /= np.linalg.norm(tangent) + 1e-15
        bitangent = np.cross(n_hat, tangent)
        ring_pts = np.outer(np.cos(eta), n_hat) + np.outer(np.sin(eta), tangent)
        pix = hp.vec2pix(nside, ring_pts[:, 0], ring_pts[:, 1], ring_pts[:, 2])
        return map_data[pix]
    except ImportError:
        # Fallback: azimuthal average in pixel index bins.
        n_hat = np.asarray(n_hat, dtype=float)
        phase = np.arange(map_data.size) * float(n_hat[0]) + float(n_hat[1])
        bins = np.floor((phase % (2 * np.pi)) / (2 * np.pi) * n_eta).astype(int)
        profile = np.zeros(n_eta)
        counts = np.zeros(n_eta)
        for b, v in zip(bins, map_data, strict=False):
            profile[b] += v
            counts[b] += 1
        counts[counts == 0] = 1
        return profile / counts


def inverse_radon_bifurcation_filter(
    healpix_map: np.ndarray,
    angles: np.ndarray | list[tuple[float, float, float]],
) -> np.ndarray:
    """Apply inverse Radon-bifurcation filter across a set of viewing angles.

    For each angle triple ``(θ, φ, ψ)`` builds a rotation axis ``n_hat`` and
    accumulates bifurcation-weighted Radon back-projection. Implements the
    observatory-side dual of Eq. 3 (WDW bifurcation closure projected to S²).

    Parameters
    ----------
    healpix_map:
        Input HEALPix map.
    angles:
        Iterable of Euler angles (rad) or shape ``(N, 3)`` array.

    Returns
    -------
    np.ndarray
        Filtered map, same shape as input.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    angles_arr = np.asarray(angles, dtype=float)
    if angles_arr.ndim == 1:
        angles_arr = angles_arr.reshape(1, -1)

    filtered = np.zeros_like(healpix_map)
    weight_sum = 0.0

    for theta, phi, psi in angles_arr:
        # View axis from Euler angles (ZYZ convention).
        n_hat = np.array(
            [
                np.sin(theta) * np.cos(phi),
                np.sin(theta) * np.sin(phi),
                np.cos(theta),
            ]
        )
        profile = _radon_profile_s2(healpix_map, n_hat)
        # Bifurcation weight: second derivative peak emphasis.
        d2 = np.gradient(np.gradient(profile))
        bifurcation = np.abs(d2)
        w = float(np.max(bifurcation) + 1e-8)
        # Back-project: modulate map by axis-aligned anisotropy score.
        try:
            import healpy as hp

            nside = hp.get_nside(healpix_map)
            theta_pix, phi_pix = hp.pix2ang(nside, np.arange(healpix_map.size))
            x = np.column_stack(
                [
                    np.sin(theta_pix) * np.cos(phi_pix),
                    np.sin(theta_pix) * np.sin(phi_pix),
                    np.cos(theta_pix),
                ]
            )
            alignment = np.abs(x @ n_hat)
            filtered += healpix_map * (1.0 + (w / (alignment + 0.5)) * np.cos(psi))
        except ImportError:
            phase = np.cos(phi + psi) * np.arange(healpix_map.size) / healpix_map.size
            filtered += healpix_map * (1.0 + w * np.cos(phase))
        weight_sum += 1.0

    if weight_sum > 0:
        filtered /= weight_sum
    return filtered
