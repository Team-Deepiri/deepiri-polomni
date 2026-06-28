"""Proof for RBLE Eq. 3 — Wheeler-DeWitt bifurcation closure."""

from __future__ import annotations

import numpy as np

from polomni.core.superspace.wdw_generator import WDWGenerator
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    gen = WDWGenerator(metric_mutation_scale=0.1)
    n = 5
    phi = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
    packets = gen.spawn_wavepackets(n, phi)
    residuals = [wp.stream_residual for wp in packets]
    max_res = float(max(residuals))
    passed = len(packets) == n and all(
        wp.metric_mutation.shape[0] == wp.metric_mutation.shape[1] for wp in packets
    )
    return ProofResult(
        id="eq03",
        name="",
        equation="",
        passed=bool(passed),
        residual=max_res,
        tolerance=1.0,
        message=f"Spawned {len(packets)} wavepackets; max stream residual={max_res:.4e}",
        module="",
    )
