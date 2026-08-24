"""Trainable tomogram → axis scar classifier (Graph-NODE companion)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from polomni.neural.datasets.loop_corpus import LoopCorpus, build_tensors
from polomni.neural.graph_node.engine import RBLEGraphEngine
from polomni.neural.train import DEFAULT_CHECKPOINT_DIR, _normalize_rows, save_checkpoint

SCAR_CHECKPOINT = "scar_classifier"


def train_scar_classifier(
    corpus: LoopCorpus,
    *,
    epochs: int = 80,
    learning_rate: float = 0.02,
    seed: int = 0,
    checkpoint_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Map tomogram fingerprints (+ parent features) → recovered scar axis."""
    tensors = build_tensors(corpus)
    n = int(tensors["tomogram_fingerprint"].shape[0])
    if n == 0:
        return {"trained": False, "reason": "empty corpus", "epochs": 0}

    parent_idx = tensors["parent_index"]
    parent_feats = []
    for i in range(n):
        p = int(parent_idx[i])
        parent_feats.append(tensors["node_features"][i, p])
    parent_feats = np.stack(parent_feats, axis=0)
    x = np.concatenate([tensors["tomogram_fingerprint"], parent_feats], axis=1)
    y = tensors["recovered_axis"]

    # Treat as 1-node "graph" so we reuse RBLEGraphEngine / checkpoint format.
    engine = RBLEGraphEngine(node_features=x.shape[1], output_dim=3, seed=seed)
    losses: list[float] = []

    if engine._ensure_torch():
        import torch

        net = engine._torch_module
        opt = torch.optim.Adam(net.parameters(), lr=learning_rate)
        x_t = torch.as_tensor(x, dtype=torch.float32).unsqueeze(1)  # (n,1,f)
        y_t = torch.as_tensor(y, dtype=torch.float32)
        for _ in range(epochs):
            opt.zero_grad()
            # forward expects (n_nodes, feat) per sample — batch manually
            preds = []
            for i in range(n):
                out = net(x_t[i])
                preds.append(out[0])
            pred = torch.stack(preds, dim=0)
            pred_u = pred / (pred.norm(dim=-1, keepdim=True) + 1e-15)
            target_u = y_t / (y_t.norm(dim=-1, keepdim=True) + 1e-15)
            loss = 1.0 - (pred_u * target_u).sum(dim=-1).mean()
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
    else:
        for _ in range(epochs):
            pred = np.stack([engine.forward(x[i : i + 1])[0] for i in range(n)], axis=0)
            pred_u = _normalize_rows(pred)
            target_u = _normalize_rows(y)
            loss = float(np.mean(1.0 - np.sum(pred_u * target_u, axis=-1)))
            losses.append(loss)
            # crude nudge toward mean target
            engine._numpy_mlp.W2 -= learning_rate * 0.02 * np.outer(
                np.ones(engine._numpy_mlp.W2.shape[0]),
                np.mean(y, axis=0),
            )

    ckpt_root = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
    path = save_checkpoint(
        engine,
        ckpt_root / SCAR_CHECKPOINT,
        kind="scar",
        meta={"epochs": epochs, "final_loss": losses[-1] if losses else None, "input_dim": int(x.shape[1])},
    )
    final = np.stack([engine.forward(x[i : i + 1])[0] for i in range(n)], axis=0)
    dots = np.clip(np.sum(_normalize_rows(final) * _normalize_rows(y), axis=-1), -1.0, 1.0)
    mean_err = float(np.mean(np.degrees(np.arccos(np.abs(dots)))))

    return {
        "trained": True,
        "epochs": epochs,
        "final_loss": losses[-1] if losses else None,
        "loss_history": losses,
        "checkpoint": str(path),
        "backend": "torch" if engine._use_torch else "numpy",
        "mean_axis_error_deg": mean_err,
        "n_samples": n,
    }


def load_scar_classifier(checkpoint_dir: Path | str | None = None) -> RBLEGraphEngine | None:
    from polomni.neural.train import load_checkpoint

    root = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
    try:
        return load_checkpoint(root / SCAR_CHECKPOINT)
    except FileNotFoundError:
        return None


def predict_axis_from_fingerprint(
    fingerprint: np.ndarray,
    parent_features: np.ndarray,
    engine: RBLEGraphEngine,
) -> np.ndarray:
    x = np.concatenate(
        [np.asarray(fingerprint, dtype=float).ravel(), np.asarray(parent_features, dtype=float).ravel()]
    )
    pred = engine.forward(x.reshape(1, -1))[0]
    return _normalize_rows(pred.reshape(1, -1))[0]
