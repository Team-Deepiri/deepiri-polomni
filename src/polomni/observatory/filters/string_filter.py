"""String-landscape filter modulating sky maps by superpotential W (Eq. 1: Λ(W,K))."""

from __future__ import annotations

from typing import Any

import numpy as np


def string_landscape_filter(healpix_map: np.ndarray, W_params: dict[str, Any]) -> np.ndarray:
    """Modulate a HEALPix map by the string landscape superpotential W.

    Implements a numeric approximation of landscape-induced modulation:

        W_eff(θ, φ) = W₀ + Σ_k A_k cos(m_k θ + n_k φ + φ_k)

    Parameters from *W_params*:
    - ``W0`` (float): baseline vacuum energy offset.
    - ``modes`` (list): each entry ``{amplitude, m, n, phase}``.
    - ``beta`` (float): coupling strength to temperature (default 1.0).

    Parameters
    ----------
    healpix_map:
        Input map (1-D HEALPix).
    W_params:
        Superpotential mode dictionary.

    Returns
    -------
    np.ndarray
        Landscape-filtered map.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    W0 = float(W_params.get("W0", 0.0))
    beta = float(W_params.get("beta", 1.0))
    modes = W_params.get("modes", [])

    try:
        import healpy as hp

        nside = hp.get_nside(healpix_map)
        theta, phi = hp.pix2ang(nside, np.arange(healpix_map.size))
    except ImportError:
        n = healpix_map.size
        theta = np.linspace(0, np.pi, n)
        phi = np.linspace(0, 2 * np.pi, n)

    W_field = np.full(healpix_map.size, W0, dtype=float)
    for mode in modes:
        amp = float(mode.get("amplitude", 1.0))
        m = int(mode.get("m", 1))
        n = int(mode.get("n", 0))
        phase = float(mode.get("phase", 0.0))
        W_field += amp * np.cos(m * theta + n * phi + phase)

    W_field -= np.mean(W_field)
    modulation = 1.0 + beta * W_field / (np.std(W_field) + 1e-12)
    return healpix_map * modulation
