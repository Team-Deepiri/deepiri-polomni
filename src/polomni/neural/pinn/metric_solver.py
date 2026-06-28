"""Physics-informed metric solver stub (Eq. 1: modified Einstein with I_μν)."""

from __future__ import annotations

from typing import Any

import numpy as np


class MetricPINN:
    """PINN stub approximating g_μν and information-stress spikes I_μν.

    When ``torch`` is available, holds a small MLP; otherwise uses analytic
    Schwarzschild-like correction from choice entropy input.
    """

    def __init__(self, dim: int = 4, hidden: int = 64) -> None:
        self.dim = dim
        self.hidden = hidden
        self._torch_net: Any | None = None

    def _minkowski(self) -> np.ndarray:
        g = np.eye(self.dim)
        g[0, 0] = -1.0
        return g

    def solve(
        self,
        coords: np.ndarray,
        choice_entropy: float,
        *,
        mass_scale: float = 1.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return metric g_μν and information tensor I_μν at *coords*.

        Parameters
        ----------
        coords:
            Shape ``(n_points, dim)`` spacetime coordinates.
        choice_entropy:
            Local choice entropy scalar (Eq. 4).
        mass_scale:
            Mass parameter for Schwarzschild-like correction.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            ``(g_munu, I_munu)`` each shape ``(n_points, dim, dim)``.
        """
        coords = np.asarray(coords, dtype=float)
        if coords.ndim == 1:
            coords = coords.reshape(1, -1)
        n = coords.shape[0]

        g = np.tile(self._minkowski(), (n, 1, 1))
        r = np.linalg.norm(coords[:, 1:], axis=1) + 1e-6
        rs = 2.0 * mass_scale
        factor = 1.0 - rs / r
        g[:, 0, 0] = -factor
        g[:, 1, 1] = 1.0 / factor
        g[:, 2, 2] = r**2
        g[:, 3, 3] = r**2 * np.sin(coords[:, 2]) ** 2

        I = np.zeros((n, self.dim, self.dim))
        spike = choice_entropy * np.exp(-r)
        I[:, 0, 0] = spike
        I[:, 1, 1] = spike * 0.5

        if self._try_torch(coords, choice_entropy) is not None:
            pass  # torch path reserved for future training loop

        return g, I

    def _try_torch(self, coords: np.ndarray, choice_entropy: float) -> Any:
        try:
            import torch
            from torch import nn

            if self._torch_net is None:

                class _Net(nn.Module):
                    def __init__(self, d: int, h: int) -> None:
                        super().__init__()
                        self.fc = nn.Linear(d + 1, h)

                    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
                        return torch.relu(self.fc(x))

                self._torch_net = _Net(coords.shape[1], self.hidden)

            x = torch.cat(
                [torch.as_tensor(coords, dtype=torch.float32),
                 torch.full((coords.shape[0], 1), choice_entropy)],
                dim=1,
            )
            return self._torch_net(x)
        except ImportError:
            return None
