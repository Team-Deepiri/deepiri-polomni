"""Unit tests for district master equation."""

import numpy as np

from omnifold_core.conductance.master_equation import district_master_step


def test_master_step_no_coupling_pure_flow() -> None:
    v = np.array([1.0, 2.0])
    f = np.array([0.5, -0.5])
    g = np.zeros((2, 2))
    kicks = np.zeros(2)
    v_next = district_master_step(v, f, g, kicks, dt=1.0)
    assert np.allclose(v_next, v + f)


def test_master_step_coupling_equalizes() -> None:
    v = np.array([0.0, 10.0])
    f = np.zeros(2)
    g = np.array([[0.0, 1.0], [1.0, 0.0]])
    kicks = np.zeros(2)
    v_next = district_master_step(v, f, g, kicks, dt=0.1)
    assert v_next[0] > v[0]
    assert v_next[1] < v[1]


def test_master_step_branch_kick() -> None:
    v = np.array([1.0])
    f = np.array([0.0])
    g = np.array([[0.0]])
    kicks = np.array([2.0])
    v_next = district_master_step(v, f, g, kicks, dt=1.0)
    assert v_next[0] == pytest.approx(3.0, rel=1e-9)


import pytest  # noqa: E402
