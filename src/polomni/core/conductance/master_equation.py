"""District graph master equation with ER bridge coupling."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def district_master_step(
    v: NDArray[np.floating],
    f: NDArray[np.floating],
    conductance: NDArray[np.floating],
    branch_kicks: NDArray[np.floating],
    dt: float,
) -> NDArray[np.float64]:
    """Euler step for dV_i/dt = F(V_i) + sum_j G_ij (V_j - V_i) + branch kicks.

    RBLE Eq. 7 discrete form on district graph nodes.
    """
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    v_vec = np.asarray(v, dtype=np.float64).ravel()
    f_vec = np.asarray(f, dtype=np.float64).ravel()
    g = np.asarray(conductance, dtype=np.float64)
    kicks = np.asarray(branch_kicks, dtype=np.float64).ravel()

    n = v_vec.size
    if f_vec.size != n or kicks.size != n:
        raise ValueError("V, F, branch_kicks must have the same length")
    if g.shape != (n, n):
        raise ValueError("conductance must be an n x n matrix")

    coupling = g @ v_vec - v_vec * g.sum(axis=1)
    dv_dt = f_vec + coupling + kicks
    return v_vec + dt * dv_dt
