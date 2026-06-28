"""Unit tests for S^2 geodesic Radon transform."""

import numpy as np
import pytest

from polomni.core.radon.transform_s2 import radon_transform_s2


def test_radon_s2_constant_map() -> None:
    nside = 4
    n_pix = 12 * nside * nside
    const_map = np.full(n_pix, 2.0)
    n_hat = np.array([0.0, 0.0, 1.0])
    value = radon_transform_s2(const_map, n_hat, eta=0.0, nside=nside)
    # Constant field: line integral ~ 2 * arc_length
    assert value == pytest.approx(2.0 * 2.0 * np.pi, rel=0.2)


def test_radon_s2_eta_shift_invariance_constant() -> None:
    nside = 2
    n_pix = 12 * nside * nside
    const_map = np.ones(n_pix)
    n_hat = np.array([1.0, 0.0, 0.0])
    v0 = radon_transform_s2(const_map, n_hat, eta=0.0, nside=nside)
    v1 = radon_transform_s2(const_map, n_hat, eta=1.0, nside=nside)
    assert v0 == pytest.approx(v1, rel=0.15)
