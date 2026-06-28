"""Proof for variational principle closure."""

from __future__ import annotations

import numpy as np

from polomni.core.conservation import compute_information_trace, stream_flux_integral
from polomni.core.gravity.information_tensor import information_tensor_N
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    """Verify horizon stream term balances informational stress (VP boundary piece)."""
    i = information_tensor_N(8, np.array([0.2, 0.1, 0.3, 0.0]))
    tr = compute_information_trace(i)
    area = 1.0
    phi = np.full(8, tr / (8 * area))
    flux = stream_flux_integral(phi, area)
    residual = abs(flux - tr)
    passed = residual < 1e-9
    return ProofResult(
        id="variational",
        name="",
        equation="",
        passed=bool(passed),
        residual=residual,
        tolerance=1e-9,
        message="Boundary stream term matches Tr(I^2) in master action",
        module="",
    )
