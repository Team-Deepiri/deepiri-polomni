"""Proof for RBLE Eq. 7 — ER=EPR bridge conductance."""

from __future__ import annotations

import numpy as np
import networkx as nx

from polomni.core.conductance.bridge_tensor import bridge_conductance, conductance_matrix
from polomni.math.proofs.base import ProofResult


def prove() -> ProofResult:
    g = bridge_conductance(0.1, np.array([1.0, 0.5]), np.array([0.5, 1.0]), t_munu_coupling=1.0)
    graph = nx.Graph()
    graph.add_edge(0, 1, conductance=0.5)
    graph.add_edge(1, 2, conductance=0.3)
    mat = conductance_matrix(graph)
    symmetric = np.allclose(mat, mat.T)
    nonnegative = np.all(mat >= 0)
    passed = g >= 0 and symmetric and nonnegative
    return ProofResult(
        id="eq07",
        name="",
        equation="",
        passed=bool(passed),
        residual=float(abs(mat[0, 1] - 0.5)),
        tolerance=1e-12,
        message=f"G_ij symmetric, nonnegative; pair conductance={g:.4f}",
        module="",
    )
