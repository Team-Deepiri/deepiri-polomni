"""Bonferroni and related multiple-testing corrections for sky searches."""

from __future__ import annotations

import math


def bonferroni_alpha(alpha: float, n_tests: int) -> float:
    """Per-test significance level after Bonferroni correction."""
    if n_tests <= 0:
        return alpha
    return alpha / float(n_tests)


def sigma_to_two_sided_p(sigma: float) -> float:
    """Convert two-sided Gaussian significance σ to p-value."""
    if sigma <= 0:
        return 1.0
    return math.erfc(sigma / math.sqrt(2.0))


def p_to_sigma(p: float) -> float:
    """Two-sided Gaussian σ from p-value (inverse of ``sigma_to_two_sided_p``)."""
    from scipy.special import erfcinv

    p = max(min(p, 1.0), 1e-300)
    return float(math.sqrt(2.0) * erfcinv(2.0 * p))


def bonferroni_corrected_p(raw_p: float, n_tests: int) -> float:
    return min(1.0, raw_p * max(n_tests, 1))


def bonferroni_corrected_sigma(raw_sigma: float, n_tests: int) -> float:
    """Adjusted significance after Bonferroni (family-wise)."""
    raw_p = sigma_to_two_sided_p(raw_sigma)
    adj_p = bonferroni_corrected_p(raw_p, n_tests)
    return p_to_sigma(adj_p)


def count_sky_search_tests(
    *,
    scan_angles: int = 36,
    hierarchical_refine_samples: int = 24,
    extra_tests: int = 0,
) -> int:
    """Estimate independent axis tests in default observatory search."""
    return max(1, scan_angles + hierarchical_refine_samples + extra_tests)


def passes_bonferroni(
    raw_sigma: float,
    n_tests: int,
    *,
    alpha: float = 0.05,
) -> tuple[bool, float, float]:
    """Return (passes, corrected_sigma, corrected_alpha)."""
    corrected_alpha = bonferroni_alpha(alpha, n_tests)
    corrected_sigma = bonferroni_corrected_sigma(raw_sigma, n_tests)
    raw_p = sigma_to_two_sided_p(raw_sigma)
    passes = raw_p <= corrected_alpha
    return passes, corrected_sigma, corrected_alpha
