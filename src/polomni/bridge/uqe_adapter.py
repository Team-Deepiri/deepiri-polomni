"""UQE-style density matrix adapter → ER=EPR conductance on district graph."""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.bridge.er_epr_coupling import map_density_to_conductance
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.core.state.stream_packet import StreamPacket


def density_matrices_from_branch_weights(
    weights: np.ndarray | list[float],
    *,
    dim: int = 2,
) -> list[np.ndarray]:
    """Build normalized density matrices from branch weights (UQE-compatible stub).

    Each branch gets a diagonal ρ with population on |0⟩ proportional to p_k.
    """
    w = np.asarray(weights, dtype=float).ravel()
    w = w / (w.sum() + 1e-15)
    matrices: list[np.ndarray] = []
    for pk in w:
        rho = np.zeros((dim, dim), dtype=complex)
        rho[0, 0] = complex(pk)
        if dim > 1:
            rho[1, 1] = complex(1.0 - pk)
        matrices.append(rho)
    return matrices


def density_matrices_from_packets(packets: list[StreamPacket], *, dim: int = 2) -> list[np.ndarray]:
    """One density matrix per stream packet from normalized branch weights."""
    return [density_matrices_from_branch_weights(pkt.branch_weights, dim=dim)[0] for pkt in packets]


def apply_uqe_conductance_to_graph(
    graph: DistrictGraph,
    parent_id: int,
    rho_list: list[np.ndarray],
    *,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Map UQE density matrices to conductance updates on parent's portal edges."""
    children = [v for u, v in graph.graph.edges() if u == parent_id]
    if not children:
        return {"updated": 0, "reason": "no children"}

    G = map_density_to_conductance(rho_list, scale=scale)
    updates: list[dict[str, float]] = []
    for idx, child in enumerate(children[: G.shape[0]]):
        old = graph.get_conductance(parent_id, child)
        new = float(G[idx, idx]) if idx < G.shape[0] else old
        if G.shape[0] > 1 and idx < G.shape[0]:
            off_diag = float(np.max(G[idx, :])) if idx < G.shape[1] else new
            new = 0.5 * (new + off_diag)
        graph.set_conductance(parent_id, child, new)
        updates.append({"child": child, "old": old, "new": new})

    return {
        "updated": len(updates),
        "conductance_matrix_shape": list(G.shape),
        "edge_updates": updates,
    }


def uqe_bridge_from_simulation(
    graph: DistrictGraph,
    packets: list[StreamPacket],
    parent_id: int,
    *,
    dim: int = 2,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Full UQE bridge: packets → density matrices → graph conductance."""
    rho_list = density_matrices_from_packets(packets, dim=dim)
    result = apply_uqe_conductance_to_graph(graph, parent_id, rho_list, scale=scale)
    result["n_density_matrices"] = len(rho_list)
    return result
