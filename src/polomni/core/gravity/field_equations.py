"""Modified Einstein field equations with information stress."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

_G_NEWTON = 1.0
_C_LIGHT = 1.0
_EIGHT_PI_G_OVER_C4 = 8.0 * np.pi * _G_NEWTON / _C_LIGHT**4


def einstein_rhs(
    t_munu: NDArray[np.floating],
    i_munu: NDArray[np.floating],
    xi: float,
) -> NDArray[np.float64]:
    """Stress side: (8 pi G / c^4) (T_mu_nu + xi I_mu_nu)."""
    t = np.asarray(t_munu, dtype=np.float64)
    i = np.asarray(i_munu, dtype=np.float64)
    if t.shape != (4, 4) or i.shape != (4, 4):
        raise ValueError("t_munu and i_munu must be 4x4")
    return _EIGHT_PI_G_OVER_C4 * (t + xi * i)


def _einstein_lhs(
    g_munu: NDArray[np.floating],
    ricci: NDArray[np.floating] | None = None,
    lambda_cc: float = 0.0,
) -> NDArray[np.float64]:
    """G_mu_nu + Lambda g_mu_nu; uses provided Ricci or flat-space proxy."""
    g = np.asarray(g_munu, dtype=np.float64)
    if g.shape != (4, 4):
        raise ValueError("g_munu must be 4x4")
    if ricci is None:
        ricci = np.zeros((4, 4), dtype=np.float64)
    r_scalar = float(np.trace(ricci))
    einstein_tensor = ricci - 0.5 * r_scalar * g
    return einstein_tensor + lambda_cc * g


def modified_field_residual(
    g_munu: NDArray[np.floating],
    t_munu: NDArray[np.floating],
    i_munu: NDArray[np.floating],
    lambda_cc: float,
    *,
    xi: float = 1.0,
    ricci: NDArray[np.floating] | None = None,
) -> NDArray[np.float64]:
    """Residual G_mu_nu + Lambda g - (8 pi G/c^4)(T + xi I); zero when satisfied."""
    lhs = _einstein_lhs(g_munu, ricci=ricci, lambda_cc=lambda_cc)
    rhs = einstein_rhs(t_munu, i_munu, xi)
    return lhs - rhs
