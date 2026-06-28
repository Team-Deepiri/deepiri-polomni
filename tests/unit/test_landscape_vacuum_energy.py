"""Unit tests for vacuum energy Lambda(W, K)."""

from polomni.core.landscape.vacuum_energy import lambda_vacuum


def test_lambda_vacuum_w_zero() -> None:
    lam = lambda_vacuum(0.0, k=0.0, m_planck=1.0, kahler_inverse=1.0)
    assert lam == pytest.approx(0.0, abs=1e-12)


def test_lambda_vacuum_negative_contribution() -> None:
    w = 1.0 + 0.0j
    k = 0.0
    lam = lambda_vacuum(w, k, m_planck=1.0, kahler_inverse=1.0)
    # exp(0) * (1 - 3) = -2
    assert lam == pytest.approx(-2.0, rel=1e-9)


def test_lambda_vacuum_uplift() -> None:
    lam = lambda_vacuum(0.0, 0.0, uplift=1e-3)
    assert lam == pytest.approx(1e-3, rel=1e-9)


import pytest  # noqa: E402
