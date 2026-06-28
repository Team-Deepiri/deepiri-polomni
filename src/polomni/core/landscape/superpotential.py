"""Flux superpotential W and Kähler covariant derivatives."""

from __future__ import annotations

from typing import Literal, overload

import numpy as np
import sympy as sp
from numpy.typing import NDArray


def superpotential_W(
    flux_integers: list[int],
    *,
    mode: Literal["numeric", "symbolic"] = "numeric",
) -> float | sp.Expr:
    """W = sum_k n_k * zeta_k with flux integers n_k wrapping CY cycles.

    Symbolic mode returns W({n_k}) as a SymPy expression.
    """
    if not flux_integers:
        raise ValueError("flux_integers must be non-empty")

    if mode == "symbolic":
        n_syms = sp.symbols(" ".join(f"n{i}" for i in range(len(flux_integers))))
        if len(flux_integers) == 1:
            n_syms = (n_syms,)
        terms = [n * sp.exp(sp.I * sp.pi * n / 7.0) for n in n_syms]
        return sp.Add(*terms)

    weights = np.exp(1j * np.pi * np.asarray(flux_integers, dtype=np.float64) / 7.0)
    return complex(np.dot(flux_integers, weights))


def kahler_metric_inverse(
    t: complex | float,
    t_bar: complex | float | None = None,
    *,
    m_planck: float = 1.0,
) -> float:
    """K^{T T̄} for single-modulus K = -3 M_P^2 ln(T + T̄)."""
    if t_bar is None:
        t_bar = np.conj(t) if np.iscomplexobj(t) else float(t)
    denom = (complex(t) + complex(t_bar)).real
    if abs(denom) < 1e-15:
        raise ValueError("T + T̄ must be non-zero")
    return float(m_planck**2 / (3.0 * denom**2))


@overload
def kahler_covariant_derivative(
    w: float | complex,
    t: complex | float,
    *,
    mode: Literal["numeric"] = "numeric",
    m_planck: float = ...,
) -> complex: ...


@overload
def kahler_covariant_derivative(
    w: sp.Expr,
    t: sp.Symbol,
    *,
    mode: Literal["symbolic"],
    m_planck: float = ...,
) -> sp.Expr: ...


def kahler_covariant_derivative(
    w: float | complex | sp.Expr,
    t: complex | float | sp.Symbol,
    *,
    mode: Literal["numeric", "symbolic"] = "numeric",
    m_planck: float = 1.0,
) -> complex | sp.Expr:
    """D_T W = d_T W + (W / M_P^2) d_T K for K = -3 M_P^2 ln(T + T̄)."""
    if mode == "symbolic":
        if not isinstance(w, sp.Expr) or not isinstance(t, sp.Symbol):
            raise TypeError("symbolic mode requires SymPy Expr and Symbol")
        d_w = sp.diff(w, t)
        d_k = -3.0 * m_planck**2 / (t + sp.conjugate(t))
        return sp.simplify(d_w + (w / m_planck**2) * d_k)

    t_c = complex(t)
    w_c = complex(w)
    d_w = 0.0 + 0.0j  # caller supplies numeric W independent of T in minimal model
    d_k = -3.0 * m_planck**2 / (t_c + np.conj(t_c))
    return complex(d_w + (w_c / m_planck**2) * d_k)


def kahler_covariant_derivative_array(
    w_values: NDArray[np.floating],
    t_values: NDArray[np.floating],
    *,
    m_planck: float = 1.0,
) -> NDArray[np.complexfloating]:
    """Vectorized D_T W for batched moduli."""
    w = np.asarray(w_values, dtype=np.complex128)
    t = np.asarray(t_values, dtype=np.complex128)
    d_k = -3.0 * m_planck**2 / (t + np.conj(t))
    return w * d_k / m_planck**2
