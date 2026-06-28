"""Proof for RBLE Eq. 5 — directed diffusion ordering."""

from __future__ import annotations

import numpy as np

from polomni.core.inflation.drift_diffusion import directed_diffusion, quantum_diffusion
from polomni.core.inflation.fokker_planck import radon_modified_D_eff
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    h = np.array([0.5, 0.6, 0.7])
    d_std = quantum_diffusion(h)
    flux = 0.5
    d_dir = directed_diffusion(flux, lambda_coupling=1.0)
    d_rad = radon_modified_D_eff(0.6, np.array([flux, flux]), lambda_coupling=1.0)
    passed = float(d_rad) > float(d_std.mean()) and float(d_dir) > 0
    return ProofResult(
        id="eq05",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(d_rad - d_std.mean()),
        tolerance=0.0,
        message=f"D_rad={d_rad:.4e} > D_std_mean={d_std.mean():.4e}",
        module="",
    )
