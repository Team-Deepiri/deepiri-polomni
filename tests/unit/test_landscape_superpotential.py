"""Unit tests for flux superpotential."""

import sympy as sp

from polomni.core.landscape.superpotential import (
    kahler_covariant_derivative,
    superpotential_W,
)


def test_superpotential_numeric_single_flux() -> None:
    w = superpotential_W([1], mode="numeric")
    expected = complex(1.0 * np.exp(1j * np.pi / 7.0))
    assert w == pytest.approx(expected, rel=1e-9)


def test_superpotential_symbolic() -> None:
    w = superpotential_W([1, 2], mode="symbolic")
    assert isinstance(w, sp.Expr)
    n0, n1 = sp.symbols("n0 n1")
    assert w.free_symbols >= {n0, n1}


def test_kahler_covariant_derivative_numeric() -> None:
    w = 1.0 + 0.5j
    t = 1.0 + 0.5j
    d = kahler_covariant_derivative(w, t, mode="numeric", m_planck=1.0)
    d_k = -3.0 / (t + np.conj(t))
    expected = w * d_k
    assert d == pytest.approx(expected, rel=1e-9)


import numpy as np  # noqa: E402
import pytest  # noqa: E402
