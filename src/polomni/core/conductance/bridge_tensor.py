"""ER=EPR bridge conductance tensor G_ij."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def bridge_conductance(
    s_euclidean: float,
    stream_i: NDArray[np.floating],
    stream_j: NDArray[np.floating],
    t_munu_coupling: float,
) -> float:
    """G_ij = exp(-S_E) * <Phi_i | T_munu | Phi_j> proxy.

    Uses Euclidean action penalty and stream overlap weighted by stress coupling.
    """
    if s_euclidean < 0.0:
        raise ValueError("s_euclidean must be non-negative")
    phi_i = np.asarray(stream_i, dtype=np.float64).ravel()
    phi_j = np.asarray(stream_j, dtype=np.float64).ravel()
    n = min(phi_i.size, phi_j.size)
    overlap = float(np.dot(phi_i[:n], phi_j[:n]))
    return float(np.exp(-s_euclidean) * t_munu_coupling * overlap)


def conductance_matrix(
    district_graph: object,
) -> NDArray[np.float64]:
    """Assemble G_ij from a NetworkX graph with edge conductance attributes."""
    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError("networkx is required for conductance_matrix") from exc

    if not isinstance(district_graph, nx.Graph):
        raise TypeError("district_graph must be a networkx Graph or DiGraph")

    nodes = list(district_graph.nodes())
    n = len(nodes)
    idx = {node: i for i, node in enumerate(nodes)}
    g_mat = np.zeros((n, n), dtype=np.float64)

    for u, v, data in district_graph.edges(data=True):
        cond = float(data.get("conductance", 0.0))
        i, j = idx[u], idx[v]
        g_mat[i, j] = cond
        g_mat[j, i] = cond

    return g_mat
