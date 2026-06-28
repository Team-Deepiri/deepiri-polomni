"""Discrete Radon transform in R^3 (RBLE district bubble scan)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def _unit_vector(xi: NDArray[np.floating]) -> NDArray[np.float64]:
    v = np.asarray(xi, dtype=np.float64).ravel()
    if v.size != 3:
        raise ValueError("xi must be a 3-vector")
    norm = np.linalg.norm(v)
    if norm < 1e-15:
        raise ValueError("xi must be non-zero")
    return v / norm


def radon_transform_r3(
    psi_field: NDArray[np.floating],
    xi: NDArray[np.floating],
    p: float,
    *,
    grid_spacing: float | NDArray[np.floating] | None = None,
    sigma: float | None = None,
) -> complex | float:
    """Evaluate R[Psi](p, xi) = integral Psi(x) delta(x·xi - p) dx on a uniform grid.

    Parameters
    ----------
    psi_field:
        3D scalar field on a Cartesian grid, shape (nx, ny, nz).
    xi:
        Unit direction of the integrating hyperplane (need not be pre-normalized).
    p:
        Signed offset along xi from the grid origin.
    grid_spacing:
        Cell volume element; scalar or per-axis spacing. Defaults to 1.
    sigma:
        Gaussian width for delta regularization. Defaults to max spacing.

    Returns
    -------
    float
        Discrete line-integral projection value (real for real psi_field).
    """
    psi = np.asarray(psi_field, dtype=np.float64)
    if psi.ndim != 3:
        raise ValueError("psi_field must have shape (nx, ny, nz)")

    xi_hat = _unit_vector(xi)
    nx, ny, nz = psi.shape

    if grid_spacing is None:
        dx = dy = dz = 1.0
    elif np.ndim(grid_spacing) == 0:
        dx = dy = dz = float(grid_spacing)
    else:
        spacing = np.asarray(grid_spacing, dtype=np.float64).ravel()
        if spacing.size == 1:
            dx = dy = dz = float(spacing[0])
        elif spacing.size == 3:
            dx, dy, dz = map(float, spacing)
        else:
            raise ValueError("grid_spacing must be scalar or length-3")

    xs = (np.arange(nx) - (nx - 1) / 2.0) * dx
    ys = (np.arange(ny) - (ny - 1) / 2.0) * dy
    zs = (np.arange(nz) - (nz - 1) / 2.0) * dz
    xg, yg, zg = np.meshgrid(xs, ys, zs, indexing="ij")
    coords = np.stack([xg, yg, zg], axis=-1)

    plane_coord = np.tensordot(coords, xi_hat, axes=([3], [0]))
    if sigma is None:
        sigma = max(dx, dy, dz)

    weights = np.exp(-0.5 * ((plane_coord - p) / sigma) ** 2)
    weights /= np.sqrt(2.0 * np.pi) * sigma
    dV = dx * dy * dz
    value = float(np.sum(psi * weights) * dV)
    return value


def radon_sinogram_r3(
    psi_field: NDArray[np.floating],
    xi: NDArray[np.floating],
    p_values: NDArray[np.floating],
    **kwargs: float,
) -> NDArray[np.float64]:
    """Vectorized Radon projection along fixed direction xi for multiple p."""
    return np.array(
        [radon_transform_r3(psi_field, xi, float(p), **kwargs) for p in p_values],
        dtype=np.float64,
    )
