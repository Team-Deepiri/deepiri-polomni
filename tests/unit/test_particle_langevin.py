"""Unit tests for polomni.core.superspace.particle_langevin."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.superspace.particle_langevin import BranchingLangevinEvolver


def test_step_harmonic_drift_without_kick() -> None:
    evolver = BranchingLangevinEvolver(mass=1.0, diffusion=0.0, seed=0)
    p = np.array([0.0])
    x = np.array([1.0])
    grad_V = np.array([1.0])

    p_new, x_new = evolver.step(p, x, dt=0.1, grad_V=grad_V, num_choices=1)

    assert p_new[0] == pytest.approx(-0.1)
    assert x_new[0] == pytest.approx(0.99)


def test_step_applies_delta_kick_at_choice_time() -> None:
    evolver = BranchingLangevinEvolver(mass=1.0, diffusion=0.0, seed=0)
    p = np.array([0.0, 0.0])
    x = np.array([0.0, 0.0])

    p_no_kick, _ = evolver.step(
        p,
        x,
        dt=0.1,
        grad_V=np.zeros(2),
        num_choices=2,
        t_choice=None,
        t_current=0.0,
        t_next=0.1,
    )
    p_kick, _ = evolver.step(
        p,
        x,
        dt=0.1,
        grad_V=np.zeros(2),
        num_choices=2,
        t_choice=0.05,
        t_current=0.0,
        t_next=0.1,
        kick_scale=1.0,
    )

    expected_kick = np.array([0.5, 1.0])
    np.testing.assert_allclose(p_kick, p_no_kick + expected_kick)


def test_evolve_trajectory_records_choice_kick() -> None:
    evolver = BranchingLangevinEvolver(mass=1.0, diffusion=0.0, seed=42)
    traj = evolver.evolve_trajectory(
        initial_p=np.array([0.0]),
        initial_x=np.array([0.0]),
        t_span=(0.0, 1.0),
        choice_times=[0.5],
        num_choices_each=[3],
        n_steps=10,
        kick_scale=0.3,
    )

    assert traj.p.shape == (11, 1)
    assert traj.x.shape == (11, 1)

    # momentum before kick step index 5 (t=0.5) vs after
    idx = 5
    kick = 0.3 * np.array([1.0 / 3.0])
    assert traj.p[idx][0] - traj.p[idx - 1][0] == pytest.approx(kick[0], rel=1e-6)

    # position continues to integrate after kick
    assert traj.x[-1][0] != pytest.approx(0.0)
