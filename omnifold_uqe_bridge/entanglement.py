"""Cross-branch entanglement gradient from UQE density matrices (Eq. 7)."""

from __future__ import annotations

import numpy as np


def cross_branch_gradient(
    rho_i: np.ndarray,
    rho_j: np.ndarray,
    H_interaction: np.ndarray | None = None,
) -> np.ndarray:
    """Compute entanglement gradient G_interact between branch density matrices.

    When ``deepiri-uqe`` is installed, attempts to use ``quantum_core`` fidelity
    helpers; otherwise uses the Hilbert-Schmidt cross-term:

        G = ρ_i ρ_j + ρ_j ρ_i - Tr(ρ_i ρ_j) I

    Parameters
    ----------
    rho_i, rho_j:
        Density matrices (square, same dimension).
    H_interaction:
        Optional interaction Hamiltonian for UQE-backed gradient.

    Returns
    -------
    np.ndarray
        Real symmetric interaction gradient matrix.
    """
    rho_i = np.asarray(rho_i, dtype=complex)
    rho_j = np.asarray(rho_j, dtype=complex)

    if H_interaction is not None:
        try:
            from quantum_core.metrics.entanglement import interaction_gradient  # type: ignore

            return np.asarray(
                interaction_gradient(rho_i, rho_j, H_interaction),
                dtype=float,
            )
        except ImportError:
            pass

    product = rho_i @ rho_j + rho_j @ rho_i
    overlap = np.trace(rho_i @ rho_j)
    dim = rho_i.shape[0]
    G = product - overlap * np.eye(dim, dtype=complex)
    return np.real(G)
