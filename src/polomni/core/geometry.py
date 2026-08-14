"""Spherical axis helpers for district coordinates and CMB imprinting."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def coordinate_to_axis(coordinate: NDArray[np.floating] | list[float]) -> np.ndarray:
    """Map district spatial coordinate to a unit vector on S²."""
    coord = np.asarray(coordinate, dtype=float).ravel()
    if coord.size < 3:
        coord = np.pad(coord, (0, 3 - coord.size))
    norm = float(np.linalg.norm(coord))
    if norm < 1e-12:
        return np.array([0.0, 0.0, 1.0], dtype=float)
    return coord / norm


def axis_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    r"""Unsigned angular separation between two axes in degrees.

    Axes are undirected: \(\hat{\mathbf{n}}\) and \(-\hat{\mathbf{n}}\) are the
    same physical axis, so the separation uses ``|a·b|``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-15)
    b = b / (np.linalg.norm(b) + 1e-15)
    dot = float(np.clip(abs(np.dot(a, b)), -1.0, 1.0))
    return float(np.degrees(np.arccos(dot)))


def align_axis_to_reference(
    axis: NDArray[np.floating] | list[float],
    reference: NDArray[np.floating] | list[float],
) -> tuple[np.ndarray, bool]:
    r"""Flip ``axis`` if needed so it lies in the same hemisphere as ``reference``.

    RBLE sky searches treat \(\hat{\mathbf{n}} \sim -\hat{\mathbf{n}}\) as one
    axis. Coordinate feedback must pull toward the nearest representative;
    otherwise mixing \(\mathbf{x}\) with its antipode shrinks and rotates the
    parent coordinate away from the intended scar direction.

    Returns
    -------
    aligned:
        Unit vector equal to ``±axis``, chosen to maximize ``aligned · reference``.
    flipped:
        ``True`` if the antipode was selected.
    """
    a = np.asarray(axis, dtype=float).ravel()
    r = np.asarray(reference, dtype=float).ravel()
    if a.size < 3:
        a = np.pad(a, (0, 3 - a.size))
    if r.size < 3:
        r = np.pad(r, (0, 3 - r.size))
    a = a / (np.linalg.norm(a) + 1e-15)
    r = r / (np.linalg.norm(r) + 1e-15)
    if float(np.dot(a, r)) < 0.0:
        return -a, True
    return a, False
