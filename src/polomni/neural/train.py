"""Train Graph-NODE predictors on loop corpus tensors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.geometry import axis_separation_deg
from polomni.neural.datasets.loop_corpus import LoopCorpus, build_tensors
from polomni.neural.graph_node.engine import RBLEGraphEngine

DEFAULT_CHECKPOINT_DIR = Path("data/neural/checkpoints")
AXIS_CHECKPOINT = "axis_predictor"
BRANCH_CHECKPOINT = "branch_predictor"


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / (norms + 1e-15)


def _axis_loss(pred: np.ndarray, target: np.ndarray) -> float:
    pred_u = _normalize_rows(pred)
    target_u = _normalize_rows(target)
    dots = np.clip(np.sum(pred_u * target_u, axis=-1), -1.0, 1.0)
    return float(np.mean(1.0 - dots))


def _branch_loss(pred: np.ndarray, target: np.ndarray) -> float:
    pred_pos = np.maximum(pred, 0.0)
    pred_sum = pred_pos.sum(axis=-1, keepdims=True)
    pred_norm = pred_pos / (pred_sum + 1e-15)
    row_mask = target.sum(axis=-1) > 0  # (n,)
    err = (pred_norm - target) ** 2
    if row_mask.any():
        return float(np.mean(err[row_mask]))
    return float(np.mean(err))


def _parent_outputs(
    engine: RBLEGraphEngine,
    node_features: np.ndarray,
    adjacency: np.ndarray,
    parent_index: np.ndarray,
) -> np.ndarray:
    outputs: list[np.ndarray] = []
    for i in range(node_features.shape[0]):
        pred = engine.forward(node_features[i], adjacency=adjacency[i])
        idx = int(parent_index[i])
        idx = min(idx, pred.shape[0] - 1)
        outputs.append(pred[idx])
    return np.stack(outputs, axis=0)


def save_checkpoint(
    engine: RBLEGraphEngine,
    path: Path,
    *,
    kind: str,
    meta: dict[str, Any] | None = None,
) -> Path:
    """Persist Graph-NODE weights to ``path`` (``.pt`` or ``.npz``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_meta = {"kind": kind, "node_features": engine.node_features, "output_dim": engine.output_dim}
    if meta:
        payload_meta.update(meta)

    if engine._ensure_torch():
        import torch

        pt_path = path.with_suffix(".pt")
        torch.save(
            {
                "state_dict": engine._torch_module.state_dict(),
                "meta": payload_meta,
            },
            pt_path,
        )
        return pt_path

    npz_path = path.with_suffix(".npz")
    np.savez(
        npz_path,
        W1=engine._numpy_mlp.W1,
        b1=engine._numpy_mlp.b1,
        W2=engine._numpy_mlp.W2,
        b2=engine._numpy_mlp.b2,
        meta=json.dumps(payload_meta),
    )
    return npz_path


def load_checkpoint(path: Path) -> RBLEGraphEngine:
    """Load a saved axis or branch predictor."""
    pt_path = path if path.suffix == ".pt" else path.with_suffix(".pt")
    npz_path = path if path.suffix == ".npz" else path.with_suffix(".npz")

    if pt_path.is_file():
        import torch

        blob = torch.load(pt_path, map_location="cpu", weights_only=False)
        meta = blob.get("meta", {})
        engine = RBLEGraphEngine(
            node_features=int(meta.get("node_features", 8)),
            output_dim=int(meta.get("output_dim", 3)),
        )
        engine._ensure_torch()
        engine._torch_module.load_state_dict(blob["state_dict"])
        return engine

    if npz_path.is_file():
        data = np.load(npz_path, allow_pickle=False)
        meta = json.loads(str(data["meta"]))
        engine = RBLEGraphEngine(
            node_features=int(meta.get("node_features", 8)),
            output_dim=int(meta.get("output_dim", 3)),
        )
        engine._numpy_mlp.W1 = np.asarray(data["W1"], dtype=float)
        engine._numpy_mlp.b1 = np.asarray(data["b1"], dtype=float)
        engine._numpy_mlp.W2 = np.asarray(data["W2"], dtype=float)
        engine._numpy_mlp.b2 = np.asarray(data["b2"], dtype=float)
        return engine

    raise FileNotFoundError(f"No checkpoint at {path} (.pt or .npz)")


def train_axis_predictor(
    corpus: LoopCorpus,
    *,
    epochs: int = 100,
    learning_rate: float = 0.01,
    seed: int = 0,
    checkpoint_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Train Graph-NODE to predict recovered axis from parent features + graph."""
    tensors = build_tensors(corpus)
    if tensors["node_features"].shape[0] == 0:
        return {"trained": False, "reason": "empty corpus", "epochs": 0}

    feat_dim = int(tensors["node_features"].shape[-1])
    engine = RBLEGraphEngine(node_features=feat_dim, output_dim=3, seed=seed)
    losses: list[float] = []

    x = tensors["node_features"]
    adj = tensors["adjacency"]
    y = tensors["recovered_axis"]
    parent_idx = tensors["parent_index"]

    if engine._ensure_torch():
        import torch
        from torch import nn

        net = engine._torch_module
        opt = torch.optim.Adam(net.parameters(), lr=learning_rate)

        for _ in range(epochs):
            opt.zero_grad()
            batch_pred = []
            for i in range(x.shape[0]):
                t_in = torch.as_tensor(x[i], dtype=torch.float32)
                out = net(t_in)
                if adj is not None:
                    a = torch.as_tensor(adj[i], dtype=torch.float32)
                    deg = torch.diag(a.sum(dim=1) + 1e-8)
                    lap = deg - a
                    t_in = t_in - 0.1 * (lap @ t_in)
                    out = net(t_in)
                idx = int(parent_idx[i])
                batch_pred.append(out[idx])
            pred_t = torch.stack(batch_pred, dim=0)
            target_t = torch.as_tensor(y, dtype=torch.float32)
            pred_u = pred_t / (pred_t.norm(dim=-1, keepdim=True) + 1e-15)
            target_u = target_t / (target_t.norm(dim=-1, keepdim=True) + 1e-15)
            loss = 1.0 - (pred_u * target_u).sum(dim=-1).mean()
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
    else:
        for _ in range(epochs):
            pred = _parent_outputs(engine, x, adj, parent_idx)
            loss = _axis_loss(pred, y)
            losses.append(loss)
            target_mean = np.mean(y, axis=0)
            engine._numpy_mlp.W2 -= learning_rate * 0.05 * np.outer(
                np.ones(engine._numpy_mlp.W2.shape[0]),
                target_mean,
            )

    ckpt_root = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
    ckpt_path = save_checkpoint(
        engine,
        ckpt_root / AXIS_CHECKPOINT,
        kind="axis",
        meta={"epochs": epochs, "final_loss": losses[-1] if losses else None},
    )

    final_pred = _parent_outputs(engine, x, adj, parent_idx)
    return {
        "trained": True,
        "epochs": epochs,
        "final_loss": losses[-1] if losses else None,
        "loss_history": losses,
        "checkpoint": str(ckpt_path),
        "backend": "torch" if engine._use_torch else "numpy",
        "mean_axis_error_deg": evaluate_axis_recovery(corpus, engine),
    }


def train_branch_predictor(
    corpus: LoopCorpus,
    *,
    epochs: int = 100,
    learning_rate: float = 0.01,
    seed: int = 0,
    checkpoint_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Train Graph-NODE to predict branch weight vectors."""
    tensors = build_tensors(corpus)
    if tensors["node_features"].shape[0] == 0:
        return {"trained": False, "reason": "empty corpus", "epochs": 0}

    feat_dim = int(tensors["node_features"].shape[-1])
    branch_dim = int(tensors["branch_weights"].shape[-1])
    engine = RBLEGraphEngine(node_features=feat_dim, output_dim=branch_dim, seed=seed)
    losses: list[float] = []

    x = tensors["node_features"]
    adj = tensors["adjacency"]
    y = tensors["branch_weights"]
    parent_idx = tensors["parent_index"]

    if engine._ensure_torch():
        import torch

        net = engine._torch_module
        opt = torch.optim.Adam(net.parameters(), lr=learning_rate)
        loss_fn = torch.nn.MSELoss()

        for _ in range(epochs):
            opt.zero_grad()
            batch_pred = []
            for i in range(x.shape[0]):
                t_in = torch.as_tensor(x[i], dtype=torch.float32)
                a = torch.as_tensor(adj[i], dtype=torch.float32)
                deg = torch.diag(a.sum(dim=1) + 1e-8)
                lap = deg - a
                t_in = t_in - 0.1 * (lap @ t_in)
                out = net(t_in)
                idx = int(parent_idx[i])
                batch_pred.append(out[idx])
            pred_t = torch.stack(batch_pred, dim=0)
            pred_pos = torch.relu(pred_t)
            pred_norm = pred_pos / (pred_pos.sum(dim=-1, keepdim=True) + 1e-15)
            target_t = torch.as_tensor(y, dtype=torch.float32)
            loss = loss_fn(pred_norm, target_t)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))
    else:
        for _ in range(epochs):
            pred = _parent_outputs(engine, x, adj, parent_idx)
            loss = _branch_loss(pred, y)
            losses.append(loss)
            target_mean = np.mean(y, axis=0)
            engine._numpy_mlp.W2 -= learning_rate * 0.05 * np.outer(
                np.ones(engine._numpy_mlp.W2.shape[0]),
                target_mean,
            )

    ckpt_root = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
    ckpt_path = save_checkpoint(
        engine,
        ckpt_root / BRANCH_CHECKPOINT,
        kind="branch",
        meta={"epochs": epochs, "final_loss": losses[-1] if losses else None},
    )

    final_pred = _parent_outputs(engine, x, adj, parent_idx)
    return {
        "trained": True,
        "epochs": epochs,
        "final_loss": losses[-1] if losses else None,
        "loss_history": losses,
        "checkpoint": str(ckpt_path),
        "backend": "torch" if engine._use_torch else "numpy",
        "final_branch_mse": _branch_loss(final_pred, y),
    }


def evaluate_axis_recovery(corpus: LoopCorpus, engine: RBLEGraphEngine) -> float:
    """Mean angular error (degrees) between predicted and recovered axes."""
    if not corpus.samples:
        return 0.0

    tensors = build_tensors(corpus)
    pred = _parent_outputs(
        engine,
        tensors["node_features"],
        tensors["adjacency"],
        tensors["parent_index"],
    )
    pred_u = _normalize_rows(pred)
    errors: list[float] = []
    for i in range(pred_u.shape[0]):
        errors.append(axis_separation_deg(pred_u[i], tensors["recovered_axis"][i]))
    return float(np.mean(errors))
