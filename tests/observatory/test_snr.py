"""Tests for formula SNR and null significance helpers."""

import numpy as np
import pytest

from polomni.observatory.scoring.snr import (
    attach_null_significance,
    empirical_p_value,
    null_moments,
    snr_from_null,
)


def test_snr_from_null_basic() -> None:
    assert snr_from_null(13.0, 10.0, 1.0) == pytest.approx(3.0)
    assert snr_from_null(10.0, 10.0, 2.0) == pytest.approx(0.0)


def test_snr_from_null_zero_sigma() -> None:
    assert snr_from_null(2.0, 1.0, 0.0) == float("inf")
    assert snr_from_null(0.0, 1.0, 0.0) == float("-inf")
    assert snr_from_null(1.0, 1.0, 0.0) == 0.0


def test_null_moments_and_p_value() -> None:
    null = [1.0, 2.0, 3.0, 4.0]
    mu, sig = null_moments(null)
    assert mu == pytest.approx(2.5)
    assert sig == pytest.approx(float(np.std(null, ddof=1)))
    # S_obs = 4 → only one null ≥ 4 → p = (1+1)/(4+1) = 0.4
    assert empirical_p_value(4.0, null) == pytest.approx(0.4)


def test_attach_null_significance_fills_bonferroni() -> None:
    null = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
    out = attach_null_significance(5.0, null, n_tests=10, family_alpha=0.05)
    assert out["snr"] > 10.0
    assert out["null_sigma"] == out["snr"]
    assert "bonferroni_pass" in out
    assert out["n_tests"] == 10
