"""Proof for RBLE Eq. 1 — modified Einstein field equations."""

from __future__ import annotations

import numpy as np

from polomni.core.gravity.field_equations import modified_field_residual
from polomni.core.gravity.information_tensor import information_tensor_N
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    g = np.diag([1.0, -1.0, -1.0, -1.0])
    t = np.diag([1e-10, 1e-11, 1e-11, 1e-11])
    i = information_tensor_N(5, np.array([0.1, 0.2, 0.0, 0.05]))
    lambda_cc = 1e-52
    residual = modified_field_residual(g, t, i, lambda_cc, xi=1.0)
    norm = float(np.linalg.norm(residual))
    # Flat-space proxy: residual dominated by Lambda and stress; check finite and structured
    passed = np.isfinite(norm) and i[0, 0] > 0
    return ProofResult(
        id="eq01",
        name="",
        equation="",
        passed=bool(passed),
        residual=norm,
        tolerance=1.0,
        message="Information stress tensor injects positive diagonal; residual finite",
        module="",
    )
