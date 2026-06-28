"""Informational Kähler potential and modulus stabilization."""

from __future__ import annotations

import numpy as np


def kahler_total(
    t: complex | float,
    t_bar: complex | float | None = None,
    i_trace: float = 0.0,
    phi_stream_flux: float = 0.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    *,
    m_planck: float = 1.0,
) -> float:
    """K_total = -3 M_P^2 ln(T + T̄) + beta Tr(I^2) + gamma oint |Phi|^2 dA.

    RBLE Eq. 8: informational back-reaction plus stream boundary term.
    """
    if t_bar is None:
        t_bar = np.conj(t) if np.iscomplexobj(t) else float(t)

    t_c = complex(t)
    t_b = complex(t_bar)
    volume_term = -3.0 * m_planck**2 * np.log(t_c + t_b).real
    info_term = beta * float(i_trace)
    stream_term = gamma * float(phi_stream_flux)
    return float(volume_term + info_term + stream_term)


def modulus_stabilization_rate(
    t: complex | float,
    d_i_trace_dt: float,
    d_flux_dt: float,
    *,
    beta: float = 1.0,
    gamma: float = 1.0,
    m_planck: float = 1.0,
) -> float:
    """d(ln T)/dt from varying K_total w.r.t. modulus T (RBLE Eq. 8 derivative)."""
    t_c = complex(t)
    return float(
        -(beta / (3.0 * m_planck**2)) * d_i_trace_dt
        - (gamma / (3.0 * m_planck**2)) * d_flux_dt
        + 0.0 * (t_c.real)  # explicit T dependence enters through ln(T+T̄) stationary piece
    )
