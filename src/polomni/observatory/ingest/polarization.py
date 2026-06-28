"""Spin-2 polarization extraction from temperature maps (observatory preprocessing)."""

from __future__ import annotations

import numpy as np


def extract_qu_maps(T_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Derive Stokes Q/U maps from a temperature map.

    When ``healpy`` is available, applies spin-2 harmonic filtering via
    ``map2alm`` / ``alm2map`` with E-mode transfer. Otherwise uses a finite-
    difference gradient proxy on the pixel ordering (less accurate but portable).

    Parameters
    ----------
    T_map:
        HEALPix temperature map (1-D, µK).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(Q_map, U_map)`` with the same shape as *T_map*.
    """
    T_map = np.asarray(T_map, dtype=float).ravel()
    try:
        import healpy as hp

        nside = hp.get_nside(T_map)
        alm = hp.map2alm(T_map)
        ell_max = 3 * nside - 1
        ells = np.arange(ell_max + 1)
        # E-mode style transfer: boost mid-ℓ for polarization proxy.
        w = np.zeros(ell_max + 1)
        w[2:] = ells[2:] * (ells[2:] + 1.0) / ((ells[2:] + 2.0) * (ells[2:] - 1.0))
        w[:2] = 0.0
        alm_e = hp.almxfl(alm, w)
        Q_map, U_map = hp.alm2map_spin([alm_e, np.zeros_like(alm_e)], nside, 2, lmax=ell_max)
        scale = 0.1 * np.std(T_map) / (np.std(Q_map) + 1e-12)
        return Q_map * scale, U_map * scale
    except ImportError:
        # Gradient-based proxy: Q ~ ∂T/∂θ, U ~ ∂T/∂φ (circular shift on ring order).
        grad = np.gradient(T_map)
        Q_map = grad
        U_map = np.roll(grad, len(grad) // 12) - np.roll(grad, -len(grad) // 12)
        scale = 0.05
        return Q_map * scale, U_map * scale
