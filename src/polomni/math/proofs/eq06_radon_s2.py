"""Proof for RBLE Eq. 6 — spherical Radon scar on S^2."""

from __future__ import annotations

import numpy as np

from polomni.core.radon.transform_s2 import radon_transform_s2
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.rble_signature import compute_rble_signature, inject_synthetic_scar
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    nside = 16
    axis = np.array([0.0, 0.0, 1.0])
    cmb = synthetic_cmb_map(nside, seed=0)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=5.0)
    n_hat = axis
    val = radon_transform_s2(scarred, n_hat, eta=0.0, nside=nside)
    report_iso = compute_rble_signature(cmb)
    report_scar = compute_rble_signature(scarred)
    passed = report_scar.rble_score > report_iso.rble_score and np.isfinite(val)
    return ProofResult(
        id="eq06",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(report_scar.rble_score - report_iso.rble_score),
        tolerance=0.0,
        message=f"Scar score {report_scar.rble_score:.4f} > iso {report_iso.rble_score:.4f}",
        module="",
    )
