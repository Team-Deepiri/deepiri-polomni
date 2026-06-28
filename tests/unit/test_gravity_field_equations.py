"""Unit tests for modified Einstein equations."""

import numpy as np

from omnifold_core.gravity.field_equations import einstein_rhs, modified_field_residual


def test_einstein_rhs_xi_scaling() -> None:
    t = np.eye(4)
    i = np.eye(4) * 2.0
    rhs1 = einstein_rhs(t, i, xi=1.0)
    rhs2 = einstein_rhs(t, i, xi=2.0)
    assert np.allclose(rhs2 - rhs1, 8.0 * np.pi * i, rtol=1e-12)


def test_modified_residual_zero_for_matched_flat() -> None:
    g = np.diag([-1.0, 1.0, 1.0, 1.0])
    t = np.zeros((4, 4))
    i = np.zeros((4, 4))
    lam = 0.0
    res = modified_field_residual(g, t, i, lam, xi=1.0, ricci=np.zeros((4, 4)))
    assert np.allclose(res, 0.0, atol=1e-12)


import pytest  # noqa: E402
