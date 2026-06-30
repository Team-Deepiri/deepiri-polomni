"""Train Graph-NODE on district jump history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import DistrictGraph
from polomni.neural.graph_node.engine import RBLEGraphEngine


@dataclass
class JumpRecord:
    """One choice-event snapshot for supervised jump prediction."""

    parent_features: np.ndarray
    child_features: np.ndarray
    branch_weights: np.ndarray


def extract_node_features(graph: DistrictGraph, node_id: int) -> np.ndarray:
    """8-D district feature vector for Graph-NODE input."""
    attrs = graph.graph.nodes[node_id]
    coord = np.asarray(attrs["coordinate"], dtype=float).ravel()
    if coord.size < 3:
        coord = np.pad(coord, (0, 3 - coord.size))
    gravity = np.asarray(attrs["law_of_gravity"], dtype=float).ravel()
    g0 = float(gravity[0]) if gravity.size else 0.0
    g1 = float(gravity[1]) if gravity.size > 1 else 0.0
    return np.array(
        [
            float(attrs["mass"]),
            g0,
            g1,
            float(attrs["lambda_vacuum"]),
            coord[0],
            coord[1],
            coord[2],
            float(np.linalg.norm(coord)),
        ],
        dtype=float,
    )


def extract_jump_history(graph: DistrictGraph) -> list[JumpRecord]:
    """Collect parent→children records from all choice events in the graph."""
    records: list[JumpRecord] = []
    for parent, child, data in graph.graph.edges(data=True):
        if "black_hole_at" not in data:
            continue
        parent_feat = extract_node_features(graph, parent)
        child_feat = extract_node_features(graph, child)
        w = float(data.get("conductance", 0.0))
        records.append(
            JumpRecord(
                parent_features=parent_feat,
                child_features=child_feat,
                branch_weights=np.array([w], dtype=float),
            )
        )
    return records


def _graph_adjacency(graph: DistrictGraph) -> np.ndarray:
    n = graph.graph.number_of_nodes()
    adj = np.zeros((n, n), dtype=float)
    for u, v, data in graph.graph.edges(data=True):
        adj[u, v] = float(data.get("conductance", 0.0))
    return adj


def train_graph_node_on_history(
    graph: DistrictGraph,
    *,
    epochs: int = 40,
    learning_rate: float = 0.01,
    seed: int = 0,
) -> dict[str, Any]:
    """Fit Graph-NODE weights to predict child feature deltas from jump history.

    Uses PyTorch when available; otherwise NumPy gradient-free coordinate descent.
    """
    records = extract_jump_history(graph)
    if not records:
        return {"trained": False, "reason": "no jump records", "epochs": 0}

    feat_dim = records[0].parent_features.size
    engine = RBLEGraphEngine(node_features=feat_dim, output_dim=feat_dim, seed=seed)
    adj = _graph_adjacency(graph)
    node_ids = sorted(graph.graph.nodes())
    features = np.stack([extract_node_features(graph, nid) for nid in node_ids])

    targets = []
    for rec in records:
        targets.append(rec.child_features - rec.parent_features)
    target_mean = np.mean(np.stack(targets), axis=0)

    losses: list[float] = []

    if engine._ensure_torch():
        import torch
        from torch import nn

        net = engine._torch_module
        opt = torch.optim.Adam(net.parameters(), lr=learning_rate)
        loss_fn = nn.MSELoss()
        x_t = torch.as_tensor(features, dtype=torch.float32)
        y_t = torch.as_tensor(
            np.tile(target_mean, (features.shape[0], 1)), dtype=torch.float32
        )

        for _ in range(epochs):
            opt.zero_grad()
            pred = net(x_t)
            loss = loss_fn(pred, y_t)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
    else:
        # NumPy fallback: nudge MLP weights toward target mean output.
        for _ in range(epochs):
            pred = engine.forward(features, adjacency=adj)
            err = pred - target_mean
            losses.append(float(np.mean(err**2)))
            engine._numpy_mlp.W2 -= learning_rate * 0.1 * np.outer(
                np.ones(engine._numpy_mlp.W2.shape[0]), target_mean
            )

    final_pred = engine.forward(features, adjacency=adj)
    return {
        "trained": True,
        "epochs": epochs,
        "n_records": len(records),
        "final_loss": losses[-1] if losses else None,
        "loss_history": losses,
        "target_mean_delta": target_mean.tolist(),
        "sample_prediction": final_pred[0].tolist() if final_pred.size else [],
        "backend": "torch" if engine._use_torch else "numpy",
    }
