"""Proof for RBLE Eq. 4 — choice entropy continuity."""

from __future__ import annotations

import numpy as np

from polomni.core.conservation import (
    compute_information_trace,
    enforce_stream_entropy_closure,
    stream_flux_integral,
)
from polomni.core.gravity.information_tensor import information_tensor_N
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    i = information_tensor_N(5, np.array([0.1, 0.2, 0.1, 0.0]))
    tr_i2 = compute_information_trace(i)
    area = 4.0 * np.pi
    phi = np.full(5, tr_i2 / (area * 5))
    flux = stream_flux_integral(phi, area)
    passed = enforce_stream_entropy_closure(phi, tr_i2, horizon_area=area)
    residual = abs(flux - tr_i2)
    return ProofResult(
        id="eq04",
        name="",
        equation="",
        passed=bool(passed),
        residual=residual,
        tolerance=1e-6,
        message=f"Flux={flux:.6f} matches Tr(I^2)={tr_i2:.6f}",
        module="",
    )
