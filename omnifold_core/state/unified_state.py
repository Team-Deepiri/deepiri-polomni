"""Unified state vector Ψ(t) for RBLE district dynamics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class UnifiedStateVector:
    """Block state vector for a spatial district in the RBLE framework.

    The unified state stacks physical and informational degrees of freedom:

        Ψ(t) = [ X_spatial ; P_momentum ; Λ_laws ; C_choice ]

    where:

    - ``X_spatial`` — spatial configuration coordinates
    - ``P_momentum`` — conjugate momentum (Hamiltonian sector)
    - ``Lambda_laws`` — local physical constants (string landscape moduli projection)
    - ``C_choice`` — multi-choice amplitudes before horizon bifurcation

    At a choice event, the branching operator ``B_k`` acts on ``C_choice`` and
    couples to the informational stress tensor ``I_μν^(N)`` in the Einstein sector.
    """

    X_spatial: NDArray[np.floating[Any]]
    P_momentum: NDArray[np.floating[Any]]
    Lambda_laws: NDArray[np.floating[Any]]
    C_choice: NDArray[np.floating[Any]]
    t: float = 0.0
    _psi_cache: NDArray[np.floating[Any]] | None = field(default=None, repr=False, compare=False)

    @property
    def Psi(self) -> NDArray[np.floating[Any]]:
        """Return the stacked unified state Ψ(t).

        Implements the RBLE state composition used by branch operators and
        Radon encapsulation pipelines.
        """
        if self._psi_cache is None:
            self._psi_cache = np.concatenate(
                [
                    np.asarray(self.X_spatial, dtype=float).ravel(),
                    np.asarray(self.P_momentum, dtype=float).ravel(),
                    np.asarray(self.Lambda_laws, dtype=float).ravel(),
                    np.asarray(self.C_choice, dtype=float).ravel(),
                ]
            )
        return self._psi_cache

    @property
    def dim(self) -> int:
        """Total dimension of Ψ(t)."""
        return int(self.Psi.size)

    def invalidate_cache(self) -> None:
        """Clear the cached Ψ(t) after in-place component mutation."""
        self._psi_cache = None

    def with_time(self, t: float) -> UnifiedStateVector:
        """Return a copy advanced to cosmological time ``t``."""
        return UnifiedStateVector(
            X_spatial=np.array(self.X_spatial, copy=True),
            P_momentum=np.array(self.P_momentum, copy=True),
            Lambda_laws=np.array(self.Lambda_laws, copy=True),
            C_choice=np.array(self.C_choice, copy=True),
            t=t,
        )

    def norm(self) -> float:
        """Euclidean norm ‖Ψ(t)‖₂."""
        return float(np.linalg.norm(self.Psi))

    def normalize(self) -> UnifiedStateVector:
        """Return a unit-norm copy of this state (Wheeler-DeWitt amplitude gauge)."""
        n = self.norm()
        if n == 0.0:
            return self.with_time(self.t)
        scale = 1.0 / n
        return UnifiedStateVector(
            X_spatial=self.X_spatial * scale,
            P_momentum=self.P_momentum * scale,
            Lambda_laws=self.Lambda_laws * scale,
            C_choice=self.C_choice * scale,
            t=self.t,
        )
