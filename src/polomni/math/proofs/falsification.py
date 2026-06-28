"""Falsification trinity proofs P1–P3."""

from __future__ import annotations

import numpy as np
import networkx as nx

from polomni.core.conductance.bridge_tensor import conductance_matrix
from polomni.core.inflation.drift_diffusion import directed_diffusion, quantum_diffusion
from polomni.core.inflation.fokker_planck import radon_modified_D_eff
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import (
    compute_rble_signature,
    inject_synthetic_scar,
)
from polomni.math.proofs.base import ProofResult


def prove_p1() -> ProofResult:
    nside = 32
    axis = np.array([0.3, 0.4, 0.85])
    axis /= np.linalg.norm(axis)
    cmb = synthetic_cmb_map(nside, seed=1)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=8.0)
    score = compute_rble_signature(scarred, axis).rble_score
    nulls = [compute_rble_signature(m).rble_score for m in generate_null_ensemble(20, nside, seed=2)]
    mu, sigma = float(np.mean(nulls)), float(np.std(nulls))
    z = (score - mu) / (sigma + 1e-12)
    passed = score > mu + 2 * sigma
    return ProofResult(
        id="fals_p1",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(z),
        tolerance=2.0,
        message=f"Injected scar z={z:.2f} sigma above null",
        module="",
    )


def prove_p2() -> ProofResult:
    h = 0.7
    d_std = float(quantum_diffusion(np.array([h]))[0])
    d_rad = radon_modified_D_eff(h, np.array([0.3, 0.4]), lambda_coupling=1.0)
    d_dir = float(directed_diffusion(0.5, lambda_coupling=1.0))
    passed = d_rad > d_std and d_dir > 0
    return ProofResult(
        id="fals_p2",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(d_rad - d_std),
        tolerance=0.0,
        message=f"D_rad > D_std ({d_rad:.4e} > {d_std:.4e})",
        module="",
    )


def prove_p3() -> ProofResult:
    g = nx.Graph()
    for i in range(4):
        g.add_edge(i, (i + 1) % 4, conductance=0.2 + 0.1 * i)
    mat = conductance_matrix(g)
    passed = np.allclose(mat, mat.T) and np.all(mat >= 0)
    return ProofResult(
        id="fals_p3",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(np.max(np.abs(mat - mat.T))),
        tolerance=1e-12,
        message="Conductance matrix symmetric and nonnegative",
        module="",
    )
