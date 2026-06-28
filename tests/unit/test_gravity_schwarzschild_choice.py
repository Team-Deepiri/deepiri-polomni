"""Unit tests for choice-modified Schwarzschild metric."""

import numpy as np

from polomni.core.gravity.schwarzschild_choice import schwarzschild_metric_with_choice


def test_schwarzschild_limit_no_choice() -> None:
    r = np.array([10.0])
    m = schwarzschild_metric_with_choice(m=1.0, i_choice=0.0, gamma=1.0, r_grid=r)
    f = -m["g_tt"][0]
    assert f == pytest.approx(1.0 - 0.2, rel=1e-12)


def test_effective_mass_increases_with_choice() -> None:
    r = np.array([20.0])
    base = schwarzschild_metric_with_choice(1.0, 0.0, 1.0, r)
    with_choice = schwarzschild_metric_with_choice(1.0, 2.0, 1.0, r)
    assert with_choice["r_s"][0] > base["r_s"][0]
    # Larger effective mass deepens the potential well: g_tt = -(1 - r_s/r).
    assert (-with_choice["g_tt"][0]) < (-base["g_tt"][0])


def test_horizon_divergence_g_rr() -> None:
    r = np.array([2.0, 2.1, 5.0])
    m = schwarzschild_metric_with_choice(1.0, 0.0, 0.0, r)
    assert m["g_rr"][2] < m["g_rr"][1]


import pytest  # noqa: E402
