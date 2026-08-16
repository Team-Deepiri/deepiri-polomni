"""Canonical RBLE SNR and null significance helpers.

CMB_OBSERVATORY_MATH.md defines:

    SNR = (S_obs − μ_null) / σ_null

``passes_bonferroni`` expects a Gaussian σ, not the raw S_RBLE score.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def snr_from_null(s_obs: float, mu_null: float, sigma_null: float) -> float:
    """SNR = (S_obs − μ_null) / σ_null."""
    s = float(s_obs)
    mu = float(mu_null)
    sig = float(sigma_null)
    if sig <= 0.0:
        if s > mu:
            return float("inf")
        if s < mu:
            return float("-inf")
        return 0.0
    return (s - mu) / sig


def empirical_p_value(s_obs: float, null_scores: NDArray[np.floating] | list[float]) -> float:
    """Monte Carlo p-value: (1 + #{S_null ≥ S_obs}) / (N + 1)."""
    null = np.asarray(null_scores, dtype=float).ravel()
    if null.size == 0:
        raise ValueError("null_scores must be non-empty")
    return (1.0 + float(np.sum(null >= float(s_obs)))) / (null.size + 1.0)


def null_moments(null_scores: NDArray[np.floating] | list[float]) -> tuple[float, float]:
    """Return (μ, σ) of a null score ensemble (sample std, ddof=1 when N>1)."""
    null = np.asarray(null_scores, dtype=float).ravel()
    if null.size == 0:
        raise ValueError("null_scores must be non-empty")
    mu = float(np.mean(null))
    if null.size == 1:
        return mu, 0.0
    return mu, float(np.std(null, ddof=1))


def attach_null_significance(
    s_obs: float,
    null_scores: NDArray[np.floating] | list[float],
    *,
    n_tests: int = 1,
    family_alpha: float = 0.05,
) -> dict[str, Any]:
    """Fill DetectionReport-style null / Bonferroni fields from a null ensemble.

    Converts formula SNR into the ``raw_sigma`` argument of ``passes_bonferroni``.
    """
    from polomni.observatory.scoring.multiple_testing import passes_bonferroni

    mu, sig = null_moments(null_scores)
    snr = snr_from_null(s_obs, mu, sig)
    p_raw = empirical_p_value(s_obs, null_scores)
    finite_snr = float(snr) if np.isfinite(snr) else (1e6 if snr > 0 else -1e6)
    bonf_pass, bonf_sigma, bonf_alpha = passes_bonferroni(
        max(finite_snr, 0.0),
        n_tests,
        alpha=family_alpha,
    )
    return {
        "null_sigma": finite_snr,
        "mu_null": mu,
        "sigma_null": sig,
        "snr": finite_snr,
        "p_value": p_raw,
        "bonferroni_pass": bonf_pass,
        "bonferroni_corrected_sigma": bonf_sigma,
        "bonferroni_alpha": bonf_alpha,
        "n_tests": int(n_tests),
    }
