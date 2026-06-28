"""Fokker-Planck drift and diffusion coefficients."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def classical_drift(
    v_prime: NDArray[np.floating],
    h: NDArray[np.floating],
) -> NDArray[np.float64]:
    """V'(phi) / (3 H(phi)) — classical slow-roll drift."""
    v = np.asarray(v_prime, dtype=np.float64)
    hub = np.asarray(h, dtype=np.float64)
    return v / (3.0 * hub + 1e-15)


def quantum_diffusion(h: NDArray[np.floating]) -> NDArray[np.float64]:
    """H^3 / (8 pi^2) — standard eternal-inflation diffusion."""
    hub = np.asarray(h, dtype=np.float64)
    if np.any(hub < 0.0):
        raise ValueError("H must be non-negative")
    return hub**3 / (8.0 * np.pi**2)


def directed_diffusion(
    stream_flux_integral: float | NDArray[np.floating],
    *,
    lambda_coupling: float = 1.0,
) -> float | NDArray[np.float64]:
    """lambda * (oint Phi dA)^2 — parent-encoded diffusion bias."""
    flux = np.asarray(stream_flux_integral, dtype=np.float64)
    return lambda_coupling * flux**2
