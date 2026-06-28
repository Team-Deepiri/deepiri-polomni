"""Isotropic null CMB ensemble for RBLE significance testing."""

from __future__ import annotations

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map


def generate_null_ensemble(
    n_maps: int,
    nside: int,
    seed: int | None = None,
) -> np.ndarray:
    """Generate *n_maps* isotropic Gaussian CMB realizations.

    Each map is drawn independently via :func:`synthetic_cmb_map`. Used to
    estimate the null distribution of S_RBLE for significance testing.

    Parameters
    ----------
    n_maps:
        Number of null realizations.
    nside:
        HEALPix resolution.
    seed:
        Master RNG seed; each map uses ``seed + i``.

    Returns
    -------
    np.ndarray
        Shape ``(n_maps, npix)`` array of null maps.
    """
    if n_maps < 1:
        raise ValueError("n_maps must be >= 1")
    maps = []
    for i in range(n_maps):
        map_seed = None if seed is None else seed + i
        maps.append(synthetic_cmb_map(nside, seed=map_seed))
    return np.stack(maps, axis=0)
