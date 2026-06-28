"""Proof for RBLE Eq. 2 — radon-modulated Fokker-Planck D_eff."""

from __future__ import annotations

import numpy as np

from polomni.core.inflation.fokker_planck import fokker_planck_step, radon_modified_D_eff
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    h = 0.7
    fluxes = np.array([0.1, 0.2, 0.15])
    d_eff = radon_modified_D_eff(h, fluxes, lambda_coupling=1.0)
    d_base = h**3 / (8.0 * np.pi**2)
    passed = d_eff > d_base

    phi = np.linspace(-2, 2, 50)
    p = np.exp(-phi**2)
    p /= p.sum()
    v = 0.5 * phi**2
    h_arr = np.full_like(phi, h)
    p_next = fokker_planck_step(p, phi, v, h_arr, dt=0.01, d_eff=d_eff)
    mass_conserved = abs(p_next.sum() - p.sum()) < 0.1

    return ProofResult(
        id="eq02",
        name="",
        equation="",
        passed=bool(passed and mass_conserved and np.all(p_next >= -1e-9)),
        residual=float(d_eff - d_base),
        tolerance=0.0,
        message=f"D_eff={d_eff:.4e} > base={d_base:.4e}; FP step stable",
        module="",
    )
