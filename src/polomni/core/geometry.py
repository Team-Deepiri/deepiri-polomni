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
    """Angular separation between two unit vectors in degrees."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-15)
    b = b / (np.linalg.norm(b) + 1e-15)
    dot = float(np.clip(abs(np.dot(a, b)), -1.0, 1.0))
    return float(np.degrees(np.arccos(dot)))
