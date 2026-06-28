"""Unit tests for R^3 Radon transform."""

import numpy as np
import pytest

from polomni.core.radon.transform_r3 import radon_transform_r3, radon_sinogram_r3


def test_radon_constant_field_unit_xi() -> None:
    """Constant psi integrates to volume * delta(0) regularization peak."""
    psi = np.ones((5, 5, 5), dtype=np.float64)
    xi = np.array([1.0, 0.0, 0.0])
    # At p=0 plane through origin, all points contribute.
    value = radon_transform_r3(psi, xi, p=0.0, grid_spacing=1.0, sigma=0.5)
    assert value > 0.0
    # Off-center plane should have smaller projection for compact support cube.
    off = radon_transform_r3(psi, xi, p=10.0, grid_spacing=1.0, sigma=0.5)
    assert off < value


def test_radon_gaussian_peak_location() -> None:
    """Gaussian centered at origin peaks at p=0 for xi along z."""
    nx = 21
    coords = np.linspace(-5, 5, nx)
    xg, yg, zg = np.meshgrid(coords, coords, coords, indexing="ij")
    psi = np.exp(-(xg**2 + yg**2 + zg**2))
    xi = np.array([0.0, 0.0, 1.0])
    at_origin = radon_transform_r3(psi, xi, p=0.0, grid_spacing=coords[1] - coords[0])
    away = radon_transform_r3(psi, xi, p=3.0, grid_spacing=coords[1] - coords[0])
    assert at_origin > away


def test_radon_sinogram_shape() -> None:
    psi = np.zeros((7, 7, 7))
    psi[3, 3, 3] = 1.0
    p_vals = np.linspace(-3, 3, 11)
    sinogram = radon_sinogram_r3(psi, np.array([1.0, 1.0, 0.0]), p_vals, sigma=0.8)
    assert sinogram.shape == (11,)
    assert np.argmax(sinogram) == pytest.approx(5, abs=2)


def test_radon_invalid_xi_raises() -> None:
    with pytest.raises(ValueError):
        radon_transform_r3(np.ones((3, 3, 3)), np.zeros(3), 0.0)
