"""Apply trained Graph-NODE predictors to live district graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.geometry import coordinate_to_axis
from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.neural.datasets.loop_corpus import NODE_FEATURE_DIM, _node_feature_vector
from polomni.neural.train import (
    AXIS_CHECKPOINT,
    BRANCH_CHECKPOINT,
    DEFAULT_CHECKPOINT_DIR,
    load_checkpoint,
)


def _unit(v: list[float] | np.ndarray) -> np.ndarray:
    a = np.asarray(v, dtype=float).ravel()
    if a.size < 3:
        a = np.pad(a, (0, 3 - a.size))
    n = float(np.linalg.norm(a[:3]))
    if n < 1e-15:
        return np.array([0.0, 0.0, 1.0])
    return a[:3] / n


def live_graph_tensors(
    graph: DistrictGraph, parent_id: int
) -> tuple[np.ndarray, np.ndarray, int]:
    nodes = list(graph.graph.nodes())
    if not nodes:
        feat = np.zeros((1, NODE_FEATURE_DIM), dtype=float)
        return feat, np.zeros((1, 1), dtype=float), 0
    id_to_idx = {nid: i for i, nid in enumerate(nodes)}
    feats = np.stack(
        [_node_feature_vector(dict(graph.graph.nodes[nid])) for nid in nodes], axis=0
    )
    n = len(nodes)
    adj = np.zeros((n, n), dtype=float)
    for u, v, attrs in graph.graph.edges(data=True):
        i, j = id_to_idx[u], id_to_idx[v]
        adj[i, j] = float(attrs.get("conductance", 1.0))
        adj[j, i] = adj[i, j]
    return feats, adj, id_to_idx.get(parent_id, 0)


class NeuralGuidance:
    """Load axis/branch Graph-NODE checkpoints and propose branching controls."""

    def __init__(self, checkpoint_dir: Path | str | None = None) -> None:
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
        self.axis_engine = None
        self.branch_engine = None
        try:
            self.axis_engine = load_checkpoint(self.checkpoint_dir / AXIS_CHECKPOINT)
        except FileNotFoundError:
            pass
        try:
            self.branch_engine = load_checkpoint(self.checkpoint_dir / BRANCH_CHECKPOINT)
        except FileNotFoundError:
            pass

    @property
    def ready(self) -> bool:
        return self.axis_engine is not None or self.branch_engine is not None

    def status(self) -> dict[str, Any]:
        return {
            "checkpoint_dir": str(self.checkpoint_dir),
            "axis": self.axis_engine is not None,
            "branch": self.branch_engine is not None,
            "ready": self.ready,
        }

    def propose(
        self,
        graph: DistrictGraph,
        parent_id: int,
        *,
        num_choices: int,
        last_recovered_axis: list[float] | np.ndarray | None = None,
    ) -> dict[str, Any]:
        """Return policy / bias_axis / branch_weights for one choice event."""
        parent_axis = coordinate_to_axis(graph.graph.nodes[parent_id]["coordinate"])
        cold_start = last_recovered_axis is None
        bias = _unit(last_recovered_axis) if not cold_start else parent_axis

        if not self.ready:
            return {
                "policy": ChoicePolicy.AXIS_BIASED,
                "bias_axis": bias.tolist(),
                "branch_weights": None,
                "source": "fallback_axis_biased",
            }

        feats, adj, pidx = live_graph_tensors(graph, parent_id)
        weights = None
        if self.axis_engine is not None:
            pred = self.axis_engine.forward(feats, adjacency=adj)
            idx = min(pidx, pred.shape[0] - 1)
            neural_axis = _unit(pred[idx])
            # Cold-start: trust rewritten history (sky-axis labels) — do not
            # dilute with the parent pole or uniform never leaves the pole.
            if cold_start:
                bias = neural_axis
            else:
                bias = _unit(0.7 * neural_axis + 0.3 * bias)
        if self.branch_engine is not None:
            pred = self.branch_engine.forward(feats, adjacency=adj)
            idx = min(pidx, pred.shape[0] - 1)
            raw = np.maximum(np.asarray(pred[idx], dtype=float).ravel()[:num_choices], 0.0)
            if raw.size < num_choices:
                raw = np.pad(raw, (0, num_choices - raw.size))
            s = float(raw.sum())
            weights = (raw / s).tolist() if s > 1e-15 else None

        return {
            "policy": ChoicePolicy.NEURAL,
            "bias_axis": bias.tolist(),
            "branch_weights": weights,
            "source": "graph_node_cold" if cold_start else "graph_node",
        }
