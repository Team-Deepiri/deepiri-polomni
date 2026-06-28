"""Boundary-state predictor at choice junctions in district graphs."""

from __future__ import annotations

import numpy as np

from polomni.neural.graph_node.engine import RBLEGraphEngine


def predict_boundary_states(
    parent_features: np.ndarray,
    num_choices: int,
    *,
    engine: RBLEGraphEngine | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Predict child boundary states and branch weights at a choice event.

    Applies the Graph-NODE engine to parent district features and softmax-
    normalizes outputs into branch weights (Eq. 4: choice entropy continuity).

    Parameters
    ----------
    parent_features:
        Feature vector or matrix for the parent district.
    num_choices:
        Number of child branches to spawn.
    engine:
        Optional pre-configured :class:`RBLEGraphEngine`.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(child_states, branch_weights)`` with weights summing to 1.
    """
    if num_choices < 1:
        raise ValueError("num_choices must be >= 1")

    parent_features = np.asarray(parent_features, dtype=float)
    if parent_features.ndim == 1:
        parent_features = parent_features.reshape(1, -1)

    if engine is None:
        engine = RBLEGraphEngine(
            node_features=parent_features.shape[1],
            output_dim=num_choices,
        )

    raw = engine.forward(parent_features)
    logits = raw[0] if raw.ndim == 2 else raw
    logits = logits[:num_choices] if logits.size >= num_choices else np.pad(
        logits, (0, num_choices - logits.size)
    )

    exp = np.exp(logits - np.max(logits))
    weights = exp / np.sum(exp)

    # Child states: parent + scaled orthogonal perturbations.
    rng = np.random.default_rng(int(np.sum(np.abs(parent_features)) * 1000) % (2**31))
    perturb = rng.standard_normal((num_choices, parent_features.shape[1])) * 0.05
    children = parent_features + perturb

    return children, weights
