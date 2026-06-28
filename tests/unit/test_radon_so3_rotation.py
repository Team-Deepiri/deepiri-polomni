"""Unit tests for SO(3) Radon bubble rotations."""

import numpy as np
import pytest

from polomni.core.radon.so3_rotation import (
    extract_particle_spectrum,
    rotate_radon_bubble,
    rotation_matrix_euler,
)


def test_rotation_matrix_identity() -> None:
    r = rotation_matrix_euler(0.0, 0.0, 0.0)
    assert np.allclose(r, np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.det(r), 1.0)


def test_rotation_matrix_orthogonality() -> None:
    r = rotation_matrix_euler(0.3, 0.7, 1.1)
    assert np.allclose(r @ r.T, np.eye(3), atol=1e-12)


def test_rotate_vector_90_deg_about_z() -> None:
    r = rotation_matrix_euler(0.0, 0.0, np.pi / 2)
    v = np.array([1.0, 0.0, 0.0])
    rotated = r @ v
    assert rotated[0] == pytest.approx(0.0, abs=1e-12)
    assert rotated[1] == pytest.approx(1.0, abs=1e-12)


def test_extract_particle_spectrum_dc_mode() -> None:
    data = np.ones(8)
    spectrum = extract_particle_spectrum(data, n_bins=4)
    assert spectrum[0] == pytest.approx(8.0, rel=1e-6)
    assert spectrum.shape == (4,)


def test_rotate_radon_bubble_1d_embedding() -> None:
    bubble = np.array([1.0, 0.0, 0.0])
    out = rotate_radon_bubble(bubble, (0.0, 0.0, np.pi / 2))
    assert out[0] == pytest.approx(0.0, abs=1e-12)
    assert out[1] == pytest.approx(1.0, abs=1e-12)
