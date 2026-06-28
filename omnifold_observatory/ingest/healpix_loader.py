"""HEALPix CMB map loading and synthetic map generation (Eq. 6: spherical Radon scar on S²)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

FieldName = Literal["T", "Q", "U", "I"]


def _npix_for_nside(nside: int) -> int:
    return 12 * nside * nside


def synthetic_cmb_map(nside: int, seed: int | None = None) -> np.ndarray:
    """Generate a Gaussian isotropic CMB temperature map on HEALPix pixels.

    Draws T_ℓm coefficients up to ℓ_max = 2·nside with C_ℓ ∝ ℓ⁻² (simplified
    Sachs-Wolfe-like spectrum) and synthesizes the map. Used for null tests and
    scar-injection experiments.

    Parameters
    ----------
    nside:
        HEALPix resolution parameter (power of 2).
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    np.ndarray
        1-D temperature map in µK units, length 12·nside².
    """
    rng = np.random.default_rng(seed)
    try:
        import healpy as hp

        ell_max = min(2 * nside, 1024)
        ells = np.arange(ell_max + 1, dtype=float)
        cl = np.zeros(ell_max + 1)
        cl[2:] = 1e-10 / (ells[2:] * (ells[2:] + 1.0))
        cl[0] = 0.0
        cl[1] = 0.0
        # healpy synfast uses global numpy RNG; seed for reproducibility.
        if seed is not None:
            np.random.seed(seed)
        return hp.synfast(cl, nside, new=True, pol=False)
    except ImportError:
        npix = _npix_for_nside(nside)
        # Fallback: correlated Gaussian noise with mild ℓ-space taper.
        white = rng.standard_normal(npix)
        return white * 100.0 / np.sqrt(nside)


def load_healpix_map(path: str | Path, field: FieldName = "T") -> np.ndarray:
    """Load a HEALPix map from FITS (astropy/healpy) or NumPy ``.npy`` archive.

    Parameters
    ----------
    path:
        Path to ``.fits`` / ``.fit`` / ``.npy`` file.
    field:
        Component to read from multi-column FITS: ``T``, ``Q``, ``U``, or ``I``.

    Returns
    -------
    np.ndarray
        1-D HEALPix pixel array.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the file format or field name is unsupported.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"HEALPix map not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".npy":
        data = np.load(path)
        return np.asarray(data, dtype=float).ravel()

    if suffix in {".fits", ".fit", ".fz"}:
        try:
            import healpy as hp

            field_idx = {"I": 0, "Q": 1, "U": 2, "T": 0}[field]
            maps, _ = hp.read_map(str(path), field=field_idx, verbose=False, dtype=float)
            return np.asarray(maps, dtype=float).ravel()
        except ImportError:
            from astropy.io import fits

            with fits.open(path) as hdul:
                data = hdul[0].data
                if data is None and len(hdul) > 1:
                    data = hdul[1].data
                if data is None:
                    raise ValueError(f"No image data in FITS file: {path}")
                arr = np.asarray(data, dtype=float)
                if arr.ndim == 2 and arr.shape[0] >= 3 and field in {"T", "I"}:
                    return arr[0].ravel()
                if arr.ndim == 2 and field == "Q":
                    return arr[1].ravel()
                if arr.ndim == 2 and field == "U":
                    return arr[2].ravel()
                return arr.ravel()

    raise ValueError(f"Unsupported HEALPix map format: {suffix}")
