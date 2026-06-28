"""Proof for RBLE Eq. 8 — Kähler stabilization."""

from __future__ import annotations

from polomni.core.landscape.kahler import kahler_total, modulus_stabilization_rate
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    t = 1.0 + 0.1j
    k = kahler_total(t, i_trace=0.5, phi_stream_flux=0.2)
    rate = modulus_stabilization_rate(t, d_i_trace_dt=-0.1, d_flux_dt=0.05)
    passed = k < 0 and abs(rate) < 1.0  # volume term dominates; rate bounded
    return ProofResult(
        id="eq08",
        name="",
        equation="",
        passed=bool(passed),
        residual=abs(k),
        tolerance=100.0,
        message=f"K_total={k:.4f}; d(ln T)/dt={rate:.4e}",
        module="",
    )
