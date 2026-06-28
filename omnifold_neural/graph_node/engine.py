"""RBLE Graph-NODE engine with optional PyTorch backend (Eq. 4: choice entropy)."""

from __future__ import annotations

from typing import Any

import numpy as np


class _NumpyMLP:
    """ReLU MLP fallback when torch is not installed."""

    def __init__(self, in_dim: int, hidden: int, out_dim: int, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.W1 = rng.standard_normal((in_dim, hidden)) * 0.1
        self.b1 = np.zeros(hidden)
        self.W2 = rng.standard_normal((hidden, out_dim)) * 0.1
        self.b2 = np.zeros(out_dim)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0, x @ self.W1 + self.b1)
        return h @ self.W2 + self.b2


class RBLEGraphEngine:
    """Graph neural dynamics engine for district DAG evolution.

    Uses ``torch.nn.Module`` when the optional ``torch`` group is installed;
    otherwise falls back to a NumPy MLP. Torch is **not** imported at module
    load time.

    Parameters
    ----------
    node_features:
        Dimension of per-district feature vectors.
    hidden_dim:
        Hidden layer width.
    output_dim:
        Output dimension (e.g. conductance deltas).
    seed:
        Weight initialization seed for the NumPy fallback.
  """

    def __init__(
        self,
        node_features: int = 8,
        hidden_dim: int = 32,
        output_dim: int = 4,
        seed: int = 0,
    ) -> None:
        self.node_features = node_features
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self._torch_module: Any | None = None
        self._numpy_mlp = _NumpyMLP(node_features, hidden_dim, output_dim, seed=seed)
        self._use_torch = False

    def _ensure_torch(self) -> bool:
        if self._torch_module is not None:
            return self._use_torch
        try:
            import torch
            from torch import nn

            class _TorchMLP(nn.Module):
                def __init__(self, in_d: int, hid: int, out_d: int) -> None:
                    super().__init__()
                    self.net = nn.Sequential(
                        nn.Linear(in_d, hid),
                        nn.ReLU(),
                        nn.Linear(hid, out_d),
                    )

                def forward(self, x: "torch.Tensor") -> "torch.Tensor":
                    return self.net(x)

            self._torch_module = _TorchMLP(self.node_features, self.hidden_dim, self.output_dim)
            self._use_torch = True
        except ImportError:
            self._use_torch = False
        return self._use_torch

    def forward(self, node_features: np.ndarray, adjacency: np.ndarray | None = None) -> np.ndarray:
        """Propagate node features through one Graph-NODE step.

        Parameters
        ----------
        node_features:
            Shape ``(n_nodes, node_features)``.
        adjacency:
            Optional adjacency matrix for neighbor aggregation.

        Returns
        -------
        np.ndarray
            Shape ``(n_nodes, output_dim)`` dynamics update.
        """
        x = np.asarray(node_features, dtype=float)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        if adjacency is not None:
            adj = np.asarray(adjacency, dtype=float)
            deg = np.diag(adj.sum(axis=1) + 1e-8)
            lap = deg - adj
            x = x - 0.1 * (lap @ x)

        if self._ensure_torch():
            import torch

            with torch.no_grad():
                t_in = torch.as_tensor(x, dtype=torch.float32)
                out = self._torch_module(t_in)
                return out.numpy()

        return np.stack([self._numpy_mlp(row) for row in x], axis=0)

    __call__ = forward
