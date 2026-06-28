"""RBLE conservation laws: stream entropy closure and horizon flux."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

# Default relative tolerance for closure checks (numerical Radon discretization).
_DEFAULT_RTOL = 1e-6
_DEFAULT_ATOL = 1e-9


class ConservationViolationError(RuntimeError):
    """Raised when RBLE stream–information conservation fails.

    Corresponds to violation of the Choice Entropy Continuity Law:

        ∫_Ω ∇_μ J^μ_choice d⁴x  =  Tr(I_μν I^μν)  =  ∮_H Φ_stream · dA
    """


def compute_information_trace(I_mu_nu: NDArray[np.floating[Any]]) -> float:
    """Compute Tr(I_μν I^μν) from the informational stress tensor.

    RBLE injects ``I_μν^(N)`` on the right-hand side of the Einstein field
    equations. The squared trace contraction measures choice-induced stress
    that must balance the Radon vacuum stream at the horizon.

    Parameters
    ----------
    I_mu_nu:
        Informational stress tensor, either 2×2 (mini-superspace reduction)
        or full 4×4 spacetime form.

    Returns
    -------
    float
        Scalar Tr(I_μν I^μν) used in entropy closure and Kähler stabilization.
    """
    tensor = np.asarray(I_mu_nu, dtype=float)
    if tensor.shape not in ((2, 2), (4, 4)):
        msg = f"I_mu_nu must be 2x2 or 4x4, got {tensor.shape}"
        raise ValueError(msg)
    if not np.allclose(tensor, tensor.T, atol=_DEFAULT_ATOL):
        msg = "I_mu_nu must be symmetric"
        raise ValueError(msg)
    contracted = tensor @ tensor
    return float(np.trace(contracted))


def stream_shannon_entropy(phi_stream: NDArray[np.floating[Any]]) -> float:
    """Shannon entropy S = -Σᵢ pᵢ log pᵢ of normalized stream amplitudes.

    Uses |Φᵢ| as non-negative weights before normalization, matching the
    log-odds source term in the choice information current.
    """
    phi = np.abs(np.asarray(phi_stream, dtype=float).ravel())
    total = float(phi.sum())
    if total <= 0.0:
        raise ValueError("phi_stream must have positive sum for entropy")
    p = phi / total
    p = np.clip(p, 1e-15, 1.0)
    return float(-np.sum(p * np.log(p)))


def stream_flux_integral(
    phi_stream: NDArray[np.floating[Any]],
    horizon_area: float,
) -> float:
    """Discrete horizon flux ∮_H Φ_stream · dA.

    For a uniform horizon discretization, the surface integral reduces to
    ``A_H * Σ_k Φ_k`` where ``Φ_k`` are branch stream amplitudes.

    Parameters
    ----------
    phi_stream:
        Stream amplitudes per branch (vacuum pipeline output).
    horizon_area:
        Horizon area A_H in code units (4π r_s² for Schwarzschild throat).

    Returns
    -------
    float
        Total flux through the graviton well horizon.
    """
    if horizon_area < 0.0:
        raise ValueError("horizon_area must be non-negative")
    phi = np.asarray(phi_stream, dtype=float).ravel()
    if phi.size == 0:
        raise ValueError("phi_stream must be non-empty")
    return float(horizon_area * np.sum(phi))


def enforce_stream_entropy_closure(
    phi_stream: NDArray[np.floating[Any]],
    information_tensor_trace: float,
    *,
    horizon_area: float = 1.0,
    rtol: float = _DEFAULT_RTOL,
    atol: float = _DEFAULT_ATOL,
) -> bool:
    """Verify RBLE stream–information closure at the horizon.

    Checks the integrated conservation bridge (RBLE Connected Equation 4):

        ∫_Ω ∇_μ J^μ_choice d⁴x  =  Tr(I_μν I^μν)  =  ∮_H Φ_stream · dA

    The discrete flux ``∮_H Φ · dA`` must match ``information_tensor_trace``
    (typically ``Tr(I_μν I^μν)`` from :func:`compute_information_trace`).

    Parameters
    ----------
    phi_stream:
        Vacuum stream amplitudes Φ_k.
    information_tensor_trace:
        Precomputed Tr(I_μν I^μν) scalar.
    horizon_area:
        Horizon area for the flux integral (default 1.0 for normalized tests).
    rtol, atol:
        Relative and absolute tolerances for ``numpy.isclose``.

    Returns
    -------
    bool
        ``True`` if closure holds; ``False`` otherwise.
    """
    flux = stream_flux_integral(phi_stream, horizon_area)
    return bool(np.isclose(flux, information_tensor_trace, rtol=rtol, atol=atol))


def assert_stream_entropy_closure(
    phi_stream: NDArray[np.floating[Any]],
    information_tensor_trace: float,
    *,
    horizon_area: float = 1.0,
    rtol: float = _DEFAULT_RTOL,
    atol: float = _DEFAULT_ATOL,
) -> None:
    """Raise :class:`ConservationViolationError` if closure fails."""
    if not enforce_stream_entropy_closure(
        phi_stream,
        information_tensor_trace,
        horizon_area=horizon_area,
        rtol=rtol,
        atol=atol,
    ):
        flux = stream_flux_integral(phi_stream, horizon_area)
        msg = (
            "RBLE conservation violation: "
            f"flux={flux:.6g}, Tr(I^2)={information_tensor_trace:.6g}"
        )
        raise ConservationViolationError(msg)
