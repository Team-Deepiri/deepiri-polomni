"""String landscape vacuum energy Lambda(W, K)."""

from __future__ import annotations

import numpy as np
import sympy as sp


def lambda_vacuum(
    w: complex | float | sp.Expr,
    k: float | sp.Expr,
    *,
    m_planck: float = 1.0,
    kahler_inverse: float | None = None,
    uplift: float = 0.0,
) -> float | sp.Expr:
    """Lambda = exp(K/M_P^2) (K^{I J} D_I W D_J W̄ - 3|W|^2/M_P^2) + uplift.

    Flux compactification formula (RBLE landscape core).
    """
    if isinstance(w, sp.Expr) or isinstance(k, sp.Expr):
        k_inv = kahler_inverse if kahler_inverse is not None else 1.0
        if isinstance(k_inv, (int, float)):
            k_inv = sp.Float(k_inv)
        d_w = sp.diff(w, sp.symbols("T", complex=True)) if w.free_symbols else sp.Integer(0)
        d_w_bar = sp.conjugate(d_w)
        w_abs_sq = sp.Abs(w) ** 2
        return sp.exp(k / m_planck**2) * (
            k_inv * d_w * d_w_bar - 3.0 * w_abs_sq / m_planck**2
        ) + uplift

    w_c = complex(w)
    k_f = float(k)
    k_inv_f = float(kahler_inverse) if kahler_inverse is not None else 1.0
    # Minimal single-modulus model: |D W|^2 ~ |W|^2 when no T-dependence in W.
    d_w_sq = abs(w_c) ** 2
    value = np.exp(k_f / m_planck**2) * (
        k_inv_f * d_w_sq - 3.0 * abs(w_c) ** 2 / m_planck**2
    ) + uplift
    return float(np.real(value))
