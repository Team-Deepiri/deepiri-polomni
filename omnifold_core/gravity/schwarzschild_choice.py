"""Schwarzschild metric with choice-induced information mass."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

_G = 1.0
_C = 1.0


def schwarzschild_metric_with_choice(
    m: float,
    i_choice: float,
    gamma: float,
    r_grid: NDArray[np.floating],
    *,
    r_s_offset: float = 0.0,
) -> dict[str, NDArray[np.float64]]:
    """Return g_tt, g_rr, g_phiphi for ds^2 with effective mass M + gamma I_choice.

    Uses geometric units G = c = 1. Coordinates: (t, r, theta, phi).
    """
    r = np.asarray(r_grid, dtype=np.float64)
    if np.any(r <= 0.0):
        raise ValueError("r_grid must be strictly positive")

    m_eff = float(m) + float(gamma) * float(i_choice)
    r_s = 2.0 * _G * m_eff / _C**2 + r_s_offset
    r_s = max(r_s, 1e-12)

    f = 1.0 - r_s / r
    f = np.clip(f, 1e-15, None)

    g_tt = -f
    g_rr = 1.0 / f
    g_phiphi = r**2

    return {
        "g_tt": g_tt,
        "g_rr": g_rr,
        "g_phiphi": g_phiphi,
        "r_s": np.full_like(r, r_s),
        "m_effective": np.full_like(r, m_eff),
    }
