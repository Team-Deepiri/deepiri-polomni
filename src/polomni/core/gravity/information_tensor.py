"""N-choice information stress tensor I_mu_nu (RBLE Eq. 1)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def information_tensor_N(
    num_choices: int,
    entropy_gradient: NDArray[np.floating],
    *,
    xi_coupling: float = 1.0,
) -> NDArray[np.float64]:
    """Build 4x4 I_mu_nu from choice count and entropy gradient.

    Diagonal components scale as xi * ln(N); off-diagonals from gradient outer product.
    """
    if num_choices < 1:
        raise ValueError("num_choices must be >= 1")
    grad = np.asarray(entropy_gradient, dtype=np.float64).ravel()
    if grad.size < 4:
        padded = np.zeros(4, dtype=np.float64)
        padded[: grad.size] = grad
        grad = padded
    else:
        grad = grad[:4]

    ln_n = np.log(float(num_choices))
    i_tensor = np.zeros((4, 4), dtype=np.float64)
    for mu in range(4):
        i_tensor[mu, mu] = xi_coupling * ln_n * (1.0 + abs(grad[mu]))
    i_tensor += np.outer(grad, grad) / (np.linalg.norm(grad) + 1e-12)
    return i_tensor


def trace_I_squared(i_mu_nu: NDArray[np.floating]) -> float:
    """Tr(I_mu_nu I^mu_nu) with Euclidean signature contraction."""
    i = np.asarray(i_mu_nu, dtype=np.float64)
    return float(np.trace(i @ i))
