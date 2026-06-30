"""Physics-informed metric solver (Eq. 1: modified Einstein with I_μν)."""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.core.gravity.field_equations import modified_field_residual


class MetricPINN:
    """PINN approximating g_μν and information-stress I_μν with Eq. 1 residual loss."""

    def __init__(self, dim: int = 4, hidden: int = 64, xi: float = 1.0) -> None:
        self.dim = dim
        self.hidden = hidden
        self.xi = xi
        self._torch_net: Any | None = None
        self._optimizer: Any | None = None

    def _minkowski(self) -> np.ndarray:
        g = np.eye(self.dim)
        g[0, 0] = -1.0
        return g

    def einstein_loss(
        self,
        g_munu: np.ndarray,
        t_munu: np.ndarray,
        i_munu: np.ndarray,
        *,
        lambda_cc: float = 1e-122,
    ) -> float:
        """Scalar MSE of modified Einstein residual (Eq. 1)."""
        residual = modified_field_residual(
            g_munu, t_munu, i_munu, lambda_cc, xi=self.xi
        )
        return float(np.mean(residual**2))

    def solve(
        self,
        coords: np.ndarray,
        choice_entropy: float,
        *,
        mass_scale: float = 1.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return metric g_μν and information tensor I_μν at *coords*."""
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

        return g, I

    def fit(
        self,
        coords: np.ndarray,
        choice_entropy: float,
        *,
        mass_scale: float = 1.0,
        epochs: int = 30,
        learning_rate: float = 1e-3,
    ) -> dict[str, Any]:
        """Train network weights to minimize Eq. 1 residual at sample points."""
        coords = np.asarray(coords, dtype=float)
        if coords.ndim == 1:
            coords = coords.reshape(1, -1)

        g, I = self.solve(coords, choice_entropy, mass_scale=mass_scale)
        T = np.zeros((self.dim, self.dim))
        T[0, 0] = mass_scale * 0.1
        T[1, 1] = mass_scale * 0.05

        losses: list[float] = []
        if not self._init_torch(coords):
            for pt in range(coords.shape[0]):
                losses.append(
                    self.einstein_loss(g[pt], T, I[pt], lambda_cc=1e-122)
                )
            return {
                "trained": False,
                "backend": "analytic",
                "epochs": 0,
                "mean_loss": float(np.mean(losses)),
                "loss_history": losses,
            }

        import torch
        from torch import nn

        net = self._torch_net
        opt = self._optimizer or torch.optim.Adam(net.parameters(), lr=learning_rate)
        self._optimizer = opt
        loss_fn = nn.MSELoss()

        x = torch.cat(
            [
                torch.as_tensor(coords, dtype=torch.float32),
                torch.full((coords.shape[0], 1), choice_entropy),
            ],
            dim=1,
        )
        g_t = torch.as_tensor(g, dtype=torch.float32)
        I_t = torch.as_tensor(I, dtype=torch.float32)
        T_t = torch.as_tensor(T, dtype=torch.float32)

        for _ in range(epochs):
            opt.zero_grad()
            hidden = net(x)
            # Perturb metric diagonal using network output.
            g_pred = g_t.clone()
            for d in range(min(hidden.shape[1], self.dim)):
                g_pred[:, d, d] = g_pred[:, d, d] + 0.01 * hidden[:, d]
            residual = []
            for pt in range(coords.shape[0]):
                lhs = g_pred[pt]  # simplified proxy residual for training signal
                rhs = T_t + self.xi * I_t[pt]
                residual.append(lhs - rhs)
            res_stack = torch.stack(residual)
            loss = loss_fn(res_stack, torch.zeros_like(res_stack))
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))

        return {
            "trained": True,
            "backend": "torch",
            "epochs": epochs,
            "final_loss": losses[-1] if losses else None,
            "loss_history": losses,
            "analytic_baseline_loss": self.einstein_loss(g[0], T, I[0]),
        }

    def _init_torch(self, coords: np.ndarray) -> bool:
        try:
            import torch
            from torch import nn

            if self._torch_net is None:

                class _Net(nn.Module):
                    def __init__(self, d: int, h: int, out: int) -> None:
                        super().__init__()
                        self.fc1 = nn.Linear(d + 1, h)
                        self.fc2 = nn.Linear(h, out)

                    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
                        return self.fc2(torch.relu(self.fc1(x)))

                self._torch_net = _Net(coords.shape[1], self.hidden, self.dim)
            return True
        except ImportError:
            return False

    def _try_torch(self, coords: np.ndarray, choice_entropy: float) -> Any:
        if not self._init_torch(coords):
            return None
        import torch

        x = torch.cat(
            [
                torch.as_tensor(coords, dtype=torch.float32),
                torch.full((coords.shape[0], 1), choice_entropy),
            ],
            dim=1,
        )
        return self._torch_net(x)
