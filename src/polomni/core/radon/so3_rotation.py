"""SO(3) gauge rotations for Radon bubble particle extraction."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def rotation_matrix_euler(
    theta: float,
    phi: float,
    psi: float,
) -> NDArray[np.float64]:
    """Active ZYZ Euler rotation matrix R(theta, phi, psi) in SO(3)."""
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    cz, sz = np.cos(psi), np.sin(psi)

    return np.array(
        [
            [
                cz * ct * cp - sz * sp,
                -sz * ct * cp - cz * sp,
                st * cp,
            ],
            [
                cz * ct * sp + sz * cp,
                -sz * ct * sp + cz * cp,
                st * sp,
            ],
            [
                -cz * st,
                sz * st,
                ct,
            ],
        ],
        dtype=np.float64,
    )


def rotate_radon_bubble(
    data: NDArray[np.floating],
    angles: tuple[float, float, float] | NDArray[np.floating],
) -> NDArray[np.float64]:
    """Apply SO(3) rotation to Radon bubble coefficients.

  For 1D spectra, rotates embedding in R^3. For 2D sheets (n_p, n_xi), applies
  rotation to the last spatial axis when shape permits.
    """
    arr = np.asarray(data, dtype=np.float64)
    if isinstance(angles, tuple):
        theta, phi, psi = angles
    else:
        a = np.asarray(angles, dtype=np.float64).ravel()
        if a.size != 3:
            raise ValueError("angles must be (theta, phi, psi)")
        theta, phi, psi = float(a[0]), float(a[1]), float(a[2])

    r = rotation_matrix_euler(theta, phi, psi)

    if arr.ndim == 1:
        if arr.size == 3:
            return r @ arr
        # Embed in R^3, rotate, return full vector.
        vec = np.zeros(3, dtype=np.float64)
        vec[: min(3, arr.size)] = arr[: min(3, arr.size)]
        return r @ vec

    if arr.ndim == 2 and arr.shape[1] == 3:
        return (r @ arr.T).T

    # Scalar field on 3D grid: rotate coordinates (inverse pull-back).
    if arr.ndim == 3:
        n = arr.shape[0]
        coords = np.stack(
            np.meshgrid(
                np.arange(n) - (n - 1) / 2.0,
                np.arange(n) - (n - 1) / 2.0,
                np.arange(n) - (n - 1) / 2.0,
                indexing="ij",
            ),
            axis=-1,
        ).reshape(-1, 3)
        rot_coords = (r @ coords.T).T.reshape(n, n, n, 3)
        # Nearest-neighbor resample for lightweight rotation.
        idx = np.round(rot_coords + (n - 1) / 2.0).astype(int)
        idx = np.clip(idx, 0, n - 1)
        out = arr[idx[..., 0], idx[..., 1], idx[..., 2]]
        return np.asarray(out, dtype=np.float64)

    raise ValueError(f"Unsupported data shape {arr.shape} for rotation")


def extract_particle_spectrum(
    rotated_data: NDArray[np.floating],
    *,
    n_bins: int | None = None,
) -> NDArray[np.float64]:
    """Extract particle spectrum amplitudes via radial FFT modes."""
    arr = np.asarray(rotated_data, dtype=np.float64)
    flat = arr.ravel()
    spectrum = np.abs(np.fft.rfft(flat))
    if n_bins is not None:
        if n_bins <= 0:
            raise ValueError("n_bins must be positive")
        if spectrum.size >= n_bins:
            return spectrum[:n_bins]
        padded = np.zeros(n_bins, dtype=np.float64)
        padded[: spectrum.size] = spectrum
        return padded
    return spectrum
