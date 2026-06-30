"""Build supervised samples from closed-loop run JSON telemetry."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_LOOP_RUNS_DIR = Path("data/loop_runs")
NODE_FEATURE_DIM = 8
TOMOGRAM_DIM = 3


@dataclass
class LoopSample:
    """One training row from a single loop step."""

    run_id: str
    step: int
    node_features: np.ndarray
    adjacency: np.ndarray
    true_axis: np.ndarray
    recovered_axis: np.ndarray
    axis_delta: np.ndarray
    branch_weights: np.ndarray
    tomogram_fingerprint: np.ndarray
    parent_index: int = 0


@dataclass
class LoopCorpus:
    """Collection of loop-step training samples."""

    samples: list[LoopSample] = field(default_factory=list)
    source_dir: Path | None = None

    @property
    def n_samples(self) -> int:
        return len(self.samples)

    @property
    def max_nodes(self) -> int:
        if not self.samples:
            return 0
        return max(s.node_features.shape[0] for s in self.samples)

    @property
    def max_branches(self) -> int:
        if not self.samples:
            return 0
        return max(s.branch_weights.size for s in self.samples)

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {
                "n_runs": 0,
                "n_samples": 0,
                "max_nodes": 0,
                "max_branches": 0,
                "mean_axis_error_deg": 0.0,
            }
        errors = [
            float(np.linalg.norm(s.axis_delta))
            for s in self.samples
        ]
        run_ids = {s.run_id for s in self.samples}
        return {
            "n_runs": len(run_ids),
            "n_samples": self.n_samples,
            "max_nodes": self.max_nodes,
            "max_branches": self.max_branches,
            "mean_axis_error_deg": float(np.mean(errors)),
            "source_dir": str(self.source_dir) if self.source_dir else None,
        }


def _normalize_axis(axis: list[float] | np.ndarray) -> np.ndarray:
    v = np.asarray(axis, dtype=float).ravel()
    if v.size < 3:
        v = np.pad(v, (0, 3 - v.size))
    norm = float(np.linalg.norm(v))
    if norm < 1e-15:
        return np.array([0.0, 0.0, 1.0], dtype=float)
    return v[:3] / norm


def _node_feature_vector(node: dict[str, Any]) -> np.ndarray:
    coord = node.get("coordinate")
    if coord is None:
        coord = [node.get("x", 0.0), node.get("y", 0.0), node.get("z", 0.0)]
    coord = np.asarray(coord, dtype=float).ravel()
    if coord.size < 3:
        coord = np.pad(coord, (0, 3 - coord.size))
    gravity = np.asarray(node.get("law_of_gravity", [0.0, 0.0]), dtype=float).ravel()
    g0 = float(gravity[0]) if gravity.size else 0.0
    g1 = float(gravity[1]) if gravity.size > 1 else 0.0
    return np.array(
        [
            float(node.get("mass", 1.0)),
            g0,
            g1,
            float(node.get("lambda_vacuum", 0.0)),
            coord[0],
            coord[1],
            coord[2],
            float(np.linalg.norm(coord)),
        ],
        dtype=float,
    )


def _parse_graph_snapshot(snapshot: dict[str, Any] | None) -> tuple[np.ndarray, np.ndarray, int]:
    if not snapshot:
        feat = np.zeros((1, NODE_FEATURE_DIM), dtype=float)
        feat[0, 0] = 1.0
        feat[0, -1] = 1.0
        return feat, np.zeros((1, 1), dtype=float), 0

    raw_nodes = snapshot.get("nodes", [])
    if not raw_nodes:
        return _parse_graph_snapshot(None)

    id_to_idx: dict[str | int, int] = {}
    features: list[np.ndarray] = []
    for node in raw_nodes:
        nid = node.get("id", len(features))
        id_to_idx[nid] = len(features)
        features.append(_node_feature_vector(node))

    n = len(features)
    adj = np.zeros((n, n), dtype=float)
    parent_index = 0
    for edge in snapshot.get("edges", []):
        src = edge.get("source", edge.get("u", 0))
        dst = edge.get("target", edge.get("v", 0))
        if src not in id_to_idx or dst not in id_to_idx:
            continue
        u, v = id_to_idx[src], id_to_idx[dst]
        w = float(edge.get("conductance", edge.get("weight", 0.0)))
        adj[u, v] = w

    if "parent_id" in snapshot:
        pid = snapshot["parent_id"]
        if pid in id_to_idx:
            parent_index = id_to_idx[pid]
    elif "active_parent" in snapshot:
        ap = snapshot["active_parent"]
        if ap in id_to_idx:
            parent_index = id_to_idx[ap]

    return np.stack(features, axis=0), adj, parent_index


def _branch_weights_from_adj(adj: np.ndarray, parent_index: int) -> np.ndarray:
    outgoing = adj[parent_index].copy()
    positive = outgoing[outgoing > 0]
    if positive.size == 0:
        return np.array([1.0], dtype=float)
    weights = positive / positive.sum()
    return weights.astype(float)


def _tomogram_fingerprint(step: dict[str, Any]) -> np.ndarray:
    detection = step.get("detection", {})
    meta = detection.get("metadata", {}) if isinstance(detection, dict) else {}

    integral = step.get("tomogram_integral", meta.get("tomogram_integral", 0.0))
    bifurcation = step.get("tomogram_bifurcation", meta.get("tomogram_bifurcation", 0.0))
    contrast = step.get("tomogram_contrast", meta.get("tomogram_contrast", 0.0))

    if contrast == 0.0 and isinstance(detection, dict):
        contrast = detection.get("tomogram_contrast", 0.0)

    return np.array([float(integral), float(bifurcation), float(contrast)], dtype=float)


def _sample_from_step(run_id: str, step: dict[str, Any], snapshot: dict[str, Any] | None) -> LoopSample | None:
    true_axis = step.get("true_axis")
    recovered_axis = step.get("recovered_axis")
    if true_axis is None or recovered_axis is None:
        return None

    true = _normalize_axis(true_axis)
    recovered = _normalize_axis(recovered_axis)
    node_features, adjacency, parent_index = _parse_graph_snapshot(snapshot)

    if "parent_id" in step:
        pid = step["parent_id"]
        id_map = {
            n.get("id", i): i
            for i, n in enumerate((snapshot or {}).get("nodes", []))
        }
        if pid in id_map:
            parent_index = id_map[pid]

    branch_weights = _branch_weights_from_adj(adjacency, parent_index)
    if "branch_weights" in step:
        branch_weights = np.asarray(step["branch_weights"], dtype=float).ravel()

    return LoopSample(
        run_id=run_id,
        step=int(step.get("step", 0)),
        node_features=node_features,
        adjacency=adjacency,
        true_axis=true,
        recovered_axis=recovered,
        axis_delta=recovered - true,
        branch_weights=branch_weights,
        tomogram_fingerprint=_tomogram_fingerprint(step),
        parent_index=parent_index,
    )


def _parse_run(path: Path) -> list[LoopSample]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    run_id = str(payload.get("run_id", path.stem))
    snapshot = payload.get("graph_snapshot")
    samples: list[LoopSample] = []

    for step in payload.get("steps", []):
        sample = _sample_from_step(run_id, step, snapshot)
        if sample is not None:
            samples.append(sample)

    return samples


def load_corpus(loop_runs_dir: Path | str | None = None) -> LoopCorpus:
    """Load all loop-run JSON files and build training samples."""
    root = Path(loop_runs_dir) if loop_runs_dir is not None else DEFAULT_LOOP_RUNS_DIR
    corpus = LoopCorpus(source_dir=root)

    if not root.is_dir():
        return corpus

    for path in sorted(root.glob("*.json")):
        try:
            corpus.samples.extend(_parse_run(path))
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            continue

    return corpus


def build_tensors(corpus: LoopCorpus) -> dict[str, np.ndarray]:
    """Pad variable-size graphs into batched NumPy tensors for training."""
    if not corpus.samples:
        return {
            "node_features": np.zeros((0, 1, NODE_FEATURE_DIM), dtype=float),
            "adjacency": np.zeros((0, 1, 1), dtype=float),
            "true_axis": np.zeros((0, 3), dtype=float),
            "recovered_axis": np.zeros((0, 3), dtype=float),
            "axis_delta": np.zeros((0, 3), dtype=float),
            "branch_weights": np.zeros((0, 1), dtype=float),
            "tomogram_fingerprint": np.zeros((0, TOMOGRAM_DIM), dtype=float),
            "parent_index": np.zeros((0,), dtype=int),
            "node_mask": np.zeros((0, 1), dtype=float),
        }

    n = corpus.n_samples
    max_nodes = corpus.max_nodes
    max_branches = max(corpus.max_branches, 1)
    feat_dim = corpus.samples[0].node_features.shape[1]

    node_features = np.zeros((n, max_nodes, feat_dim), dtype=float)
    adjacency = np.zeros((n, max_nodes, max_nodes), dtype=float)
    true_axis = np.zeros((n, 3), dtype=float)
    recovered_axis = np.zeros((n, 3), dtype=float)
    axis_delta = np.zeros((n, 3), dtype=float)
    branch_weights = np.zeros((n, max_branches), dtype=float)
    tomogram = np.zeros((n, TOMOGRAM_DIM), dtype=float)
    parent_index = np.zeros((n,), dtype=int)
    node_mask = np.zeros((n, max_nodes), dtype=float)

    for i, sample in enumerate(corpus.samples):
        nn = sample.node_features.shape[0]
        node_features[i, :nn] = sample.node_features
        adjacency[i, :nn, :nn] = sample.adjacency
        true_axis[i] = sample.true_axis
        recovered_axis[i] = sample.recovered_axis
        axis_delta[i] = sample.axis_delta
        nb = sample.branch_weights.size
        branch_weights[i, :nb] = sample.branch_weights
        tomogram[i] = sample.tomogram_fingerprint
        parent_index[i] = sample.parent_index
        node_mask[i, :nn] = 1.0

    return {
        "node_features": node_features,
        "adjacency": adjacency,
        "true_axis": true_axis,
        "recovered_axis": recovered_axis,
        "axis_delta": axis_delta,
        "branch_weights": branch_weights,
        "tomogram_fingerprint": tomogram,
        "parent_index": parent_index,
        "node_mask": node_mask,
    }
