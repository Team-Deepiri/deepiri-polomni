"""RBLE signature timing benchmarks for stack verification."""

from __future__ import annotations

import time
from typing import Any

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.rble_signature import compute_rble_signature


def time_rble_signature(nside: int, *, seed: int = 42) -> dict[str, Any]:
    """Profile :func:`compute_rble_signature` at a given HEALPix resolution."""
    cmb = synthetic_cmb_map(nside, seed=seed)
    t0 = time.perf_counter()
    report = compute_rble_signature(cmb)
    elapsed = time.perf_counter() - t0
    return {
        "nside": nside,
        "npix": int(cmb.size),
        "seconds": elapsed,
        "rble_score": float(report.rble_score),
    }


def run_benchmark_suite(nsides: list[int] | None = None) -> list[dict[str, Any]]:
    """Run timing benchmarks across a default NSIDE ladder."""
    ladder = nsides or [16, 32, 64]
    return [time_rble_signature(n) for n in ladder]
