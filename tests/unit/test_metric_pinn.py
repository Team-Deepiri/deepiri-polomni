"""Unit tests for MetricPINN Eq. 1 loss."""

from __future__ import annotations

import numpy as np

from polomni.neural.pinn.metric_solver import MetricPINN


def test_einstein_loss_nonnegative() -> None:
    pinn = MetricPINN()
    g, I = pinn.solve(np.array([0, 1.5, 0.5, 0.0]), choice_entropy=0.5)
    T = np.zeros((4, 4))
    T[0, 0] = 0.1
    loss = pinn.einstein_loss(g[0], T, I[0])
    assert loss >= 0.0


def test_fit_returns_history() -> None:
    pinn = MetricPINN()
    coords = np.array([[0, 1.0, 0.5, 0.0], [0, 2.0, 1.0, 0.0]])
    result = pinn.fit(coords, choice_entropy=0.7, epochs=5)
    assert "mean_loss" in result or "final_loss" in result
