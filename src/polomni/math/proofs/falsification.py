"""Falsification trinity proofs P1–P3."""

from __future__ import annotations

import numpy as np
import networkx as nx

from polomni.core.conductance.bridge_tensor import conductance_matrix
from polomni.core.inflation.drift_diffusion import directed_diffusion, quantum_diffusion
from polomni.core.inflation.fokker_planck import radon_modified_D_eff
from polomni.math.proofs.base import ProofResult
from polomni.math.proofs.baselines import check_within
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import (
    compute_rble_signature,
    inject_synthetic_scar,
)


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
    passed_base, residual, msg = check_within("fals_p1", {"injection_z": float(z)})
    passed = bool(passed_base and score > mu + 2 * sigma)
    return ProofResult(
        id="fals_p1",
        name="P1 CMB scar injection",
        equation="synthetic null ensemble",
        passed=passed,
        residual=float(z),
        tolerance=2.0,
        message=f"Injected scar z={z:.2f}σ above null; {msg}",
        module="polomni.math.proofs.falsification",
    )


def prove_p2() -> ProofResult:
    h = 0.7
    d_std = float(quantum_diffusion(np.array([h]))[0])
    d_rad = radon_modified_D_eff(h, np.array([0.3, 0.4]), lambda_coupling=1.0)
    d_dir = float(directed_diffusion(0.5, lambda_coupling=1.0))
    excess = float(d_rad - d_std)
    passed_base, residual, msg = check_within("fals_p2", {"d_rad_minus_std": excess})
    passed = bool(passed_base and d_rad > d_std and d_dir > 0)
    return ProofResult(
        id="fals_p2",
        name="P2 directed D_eff",
        equation="D_rad > D_std",
        passed=passed,
        residual=excess,
        tolerance=0.0,
        message=f"D_rad={d_rad:.4e} > D_std={d_std:.4e}; {msg}",
        module="polomni.math.proofs.falsification",
    )


def prove_p3() -> ProofResult:
    g = nx.Graph()
    for i in range(4):
        g.add_edge(i, (i + 1) % 4, conductance=0.2 + 0.1 * i)
    mat = conductance_matrix(g)
    sym_res = float(np.max(np.abs(mat - mat.T)))
    passed_base, residual, msg = check_within("fals_p3", {"symmetry_residual": sym_res})
    passed = bool(passed_base and np.all(mat >= 0))
    return ProofResult(
        id="fals_p3",
        name="P3 conductance symmetry",
        equation="G_ij = G_ji",
        passed=passed,
        residual=sym_res,
        tolerance=1e-12,
        message=f"Conductance matrix symmetric; {msg}",
        module="polomni.math.proofs.falsification",
    )
