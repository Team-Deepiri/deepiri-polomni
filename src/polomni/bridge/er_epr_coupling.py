"""Map UQE density matrices to ER=EPR conductance tensor G_ij (Eq. 7)."""

from __future__ import annotations

import numpy as np

from polomni.bridge.entanglement import cross_branch_gradient


def map_density_to_conductance(
    rho_list: list[np.ndarray],
    *,
    scale: float = 1.0,
) -> np.ndarray:
    """Build conductance matrix G_ij from a list of branch density matrices.

    Off-diagonal entries derive from :func:`cross_branch_gradient`; diagonal
    entries use von Neumann entropy as local conductance capacity.

    Parameters
    ----------
    rho_list:
        List of density matrices, one per district branch.
    scale:
        Global scaling factor for conductance.

    Returns
    -------
    np.ndarray
        Real symmetric conductance matrix, shape ``(n, n)``.
    """
    n = len(rho_list)
    if n == 0:
        return np.zeros((0, 0))

    G = np.zeros((n, n), dtype=float)
    for i in range(n):
        rho_i = np.asarray(rho_list[i], dtype=complex)
        evals = np.linalg.eigvalsh(rho_i)
        evals = np.clip(evals.real, 1e-15, 1.0)
        G[i, i] = float(-np.sum(evals * np.log(evals)))

    for i in range(n):
        for j in range(i + 1, n):
            grad = cross_branch_gradient(
                np.asarray(rho_list[i], dtype=complex),
                np.asarray(rho_list[j], dtype=complex),
            )
            val = scale * float(np.linalg.norm(grad, ord="fro"))
            G[i, j] = val
            G[j, i] = val

    return G
