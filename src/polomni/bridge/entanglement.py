"""Cross-branch entanglement gradient between sector density matrices (RBLE Eq. 7)."""

from __future__ import annotations

import numpy as np


def cross_branch_gradient(
    rho_i: np.ndarray,
    rho_j: np.ndarray,
    H_interaction: np.ndarray | None = None,
) -> np.ndarray:
    """Compute entanglement gradient G_interact between branch density matrices.

    NumPy-native Hilbert-Schmidt cross-term (no external quantum engine required):

        G = ρ_i ρ_j + ρ_j ρ_i - Tr(ρ_i ρ_j) I

    Parameters
    ----------
    rho_i, rho_j:
        Density matrices (square, same dimension).
    H_interaction:
        Optional interaction Hamiltonian (reserved for future extensions).

    Returns
    -------
    np.ndarray
        Real symmetric interaction gradient matrix.
    """
    rho_i = np.asarray(rho_i, dtype=complex)
    rho_j = np.asarray(rho_j, dtype=complex)

    if H_interaction is not None:
        H = np.asarray(H_interaction, dtype=complex)
        commutator = rho_i @ H @ rho_j - rho_j @ H @ rho_i
        return np.real(commutator)

    product = rho_i @ rho_j + rho_j @ rho_i
    overlap = np.trace(rho_i @ rho_j)
    dim = rho_i.shape[0]
    G = product - overlap * np.eye(dim, dtype=complex)
    return np.real(G)
