"""Choice-spawning branch operators for unified state Ψ(t) (RBLE Eq. 4)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from polomni.core.state.unified_state import UnifiedStateVector


class BranchOperator:
    r"""Vectorized choice-spawning operator ``B_k`` on superspace amplitudes.

    The branching superoperator acts on the choice sector of Ψ(t):

        B_k |Ψ⟩ = |Ψ_k⟩,    w_k = \mathrm{softmax}(\log \mathrm{odds}(C))

    where ``C_choice`` encodes pre-horizon log-odds amplitudes and ``w_k`` are
    the normalized branch weights used by Wheeler-DeWitt injection and conductance
    updates.
    """

    def B_k(
        self,
        psi: NDArray[np.floating],
        k: int,
        num_choices: int,
    ) -> NDArray[np.floating]:
        """Apply the ``k``-th choice-spawning operator to a state vector ``ψ``.

        For a batch matrix ``ψ`` with shape ``(batch, dim)``, the operator
        cyclically permutes the trailing choice block by ``k`` slots:

            (B_k ψ)_{choice} = roll(C_choice, k)

        preserving ‖ψ‖₂ (orthogonal branch relabeling in the WDW gauge).

        Parameters
        ----------
        psi:
            Unified state vector or batch thereof.
        k:
            Branch index in ``[0, num_choices)``.
        num_choices:
            Total number of branches ``N`` at the choice event.

        Returns
        -------
        NDArray
            Transformed state with the same shape as ``psi``.
        """
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")
        if not 0 <= k < num_choices:
            raise ValueError(f"branch index k={k} out of range for N={num_choices}")

        arr = np.asarray(psi, dtype=float)
        single = arr.ndim == 1
        if single:
            arr = arr.reshape(1, -1)

        choice_width = num_choices
        if arr.shape[1] < choice_width:
            raise ValueError(
                f"psi dimension {arr.shape[1]} smaller than choice block width {choice_width}"
            )

        out = arr.copy()
        choice_start = arr.shape[1] - choice_width
        out[:, choice_start:] = np.roll(arr[:, choice_start:], shift=k, axis=1)

        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        out = out / norms

        return out[0] if single else out

    def compute_branch_weights(
        self,
        choice_vector: NDArray[np.floating],
        num_choices: int,
    ) -> NDArray[np.floating]:
        r"""Compute branch weights via softmax of log-odds amplitudes.

            w_k = \frac{\exp(\ell_k)}{\sum_j \exp(\ell_j)},

        where ``ℓ_k = log(p_k / (1 - p_k))`` for probabilities ``p_k`` derived
        from the leading ``num_choices`` entries of ``choice_vector``.
        """
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")

        vec = np.asarray(choice_vector, dtype=float).ravel()
        if vec.size < num_choices:
            raise ValueError(
                f"choice_vector length {vec.size} < num_choices {num_choices}"
            )

        probs = _to_probabilities(vec[:num_choices])
        log_odds = np.log(probs / (1.0 - probs))
        return _softmax(log_odds)

    def split_state_vector(
        self,
        unified_state: UnifiedStateVector,
        num_choices: int,
    ) -> list[UnifiedStateVector]:
        """Split a parent unified state into ``num_choices`` branch copies.

        Each child state carries a one-hot ``C_choice`` amplitude scaled by the
        corresponding softmax branch weight, preserving spatial and momentum blocks.
        """
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")

        weights = self.compute_branch_weights(unified_state.C_choice, num_choices)
        branches: list[UnifiedStateVector] = []

        for k in range(num_choices):
            c_branch = np.zeros(num_choices, dtype=float)
            c_branch[k] = float(weights[k])

            branches.append(
                UnifiedStateVector(
                    X_spatial=np.array(unified_state.X_spatial, copy=True),
                    P_momentum=np.array(unified_state.P_momentum, copy=True),
                    Lambda_laws=np.array(unified_state.Lambda_laws, copy=True),
                    C_choice=c_branch,
                    t=unified_state.t,
                )
            )

        return branches


def _to_probabilities(values: NDArray[np.floating]) -> NDArray[np.floating]:
    """Map arbitrary amplitudes to open-interval probabilities via sigmoid."""
    shifted = values - np.max(values)
    exp_vals = np.exp(shifted)
    raw = exp_vals / np.sum(exp_vals)
    eps = 1e-12
    return np.clip(raw, eps, 1.0 - eps)


def _softmax(log_odds: NDArray[np.floating]) -> NDArray[np.floating]:
    shifted = log_odds - np.max(log_odds)
    exp_vals = np.exp(shifted)
    return exp_vals / np.sum(exp_vals)
