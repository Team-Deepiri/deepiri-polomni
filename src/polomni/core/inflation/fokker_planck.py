"""Radon-modulated Fokker-Planck evolution (RBLE Eq. 5)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def radon_modified_D_eff(
    h: float,
    stream_fluxes: NDArray[np.floating],
    lambda_coupling: float,
) -> float:
    """D_eff = H^3/(8 pi^2) + lambda * sum_k w_k ||Phi_stream||^2."""
    h_f = float(h)
    if h_f < 0.0:
        raise ValueError("Hubble parameter H must be non-negative")
    base = h_f**3 / (8.0 * np.pi**2)
    fluxes = np.asarray(stream_fluxes, dtype=np.float64).ravel()
    stream_term = lambda_coupling * float(np.sum(fluxes**2))
    return float(base + stream_term)


def fokker_planck_step(
    p: NDArray[np.floating],
    phi: NDArray[np.floating],
    v: NDArray[np.floating],
    h: NDArray[np.floating],
    dt: float,
    d_eff: float | NDArray[np.floating],
) -> NDArray[np.float64]:
    """Explicit Euler step for dP/dt = d_phi[ V'/(3H) P ] + D_eff d_phi^2 P."""
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    p_arr = np.asarray(p, dtype=np.float64)
    phi_arr = np.asarray(phi, dtype=np.float64)
    v_arr = np.asarray(v, dtype=np.float64)
    h_arr = np.asarray(h, dtype=np.float64)

    if not (p_arr.shape == phi_arr.shape == v_arr.shape == h_arr.shape):
        raise ValueError("P, phi, V, H must share the same shape")

    d_phi = phi_arr[1] - phi_arr[0] if phi_arr.size > 1 else 1.0
    v_prime = np.gradient(v_arr, d_phi)
    drift = v_prime / (3.0 * h_arr + 1e-15)

    flux = drift * p_arr
    d_flux = np.gradient(flux, d_phi)

    if np.ndim(d_eff) == 0:
        d_arr = np.full_like(p_arr, float(d_eff))
    else:
        d_arr = np.asarray(d_eff, dtype=np.float64)
        if d_arr.shape != p_arr.shape:
            raise ValueError("d_eff must be scalar or match P shape")

    d2_p = np.gradient(np.gradient(p_arr, d_phi), d_phi)
    diffusion_term = d_arr * d2_p

    dp_dt = d_flux + diffusion_term
    return p_arr + dt * dp_dt
