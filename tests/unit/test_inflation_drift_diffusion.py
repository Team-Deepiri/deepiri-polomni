"""Unit tests for drift and diffusion coefficients."""

import numpy as np

from polomni.core.inflation.drift_diffusion import (
    classical_drift,
    directed_diffusion,
    quantum_diffusion,
)


def test_quantum_diffusion_h3_scaling() -> None:
    h = np.array([1.0, 2.0])
    d = quantum_diffusion(h)
    assert d[1] / d[0] == pytest.approx(8.0, rel=1e-9)


def test_classical_drift_sign() -> None:
    v_prime = np.array([1.0])
    h = np.array([3.0])
    drift = classical_drift(v_prime, h)
    assert drift[0] == pytest.approx(1.0 / 9.0, rel=1e-9)


def test_directed_diffusion_quadratic() -> None:
    assert directed_diffusion(2.0, lambda_coupling=0.5) == pytest.approx(2.0, rel=1e-9)


import pytest  # noqa: E402
