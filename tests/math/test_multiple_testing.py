"""Tests for Bonferroni multiple-testing helpers."""

from polomni.observatory.scoring.multiple_testing import (
    bonferroni_corrected_sigma,
    passes_bonferroni,
    sigma_to_two_sided_p,
)


def test_bonferroni_reduces_significance() -> None:
    raw = 5.0
    corrected = bonferroni_corrected_sigma(raw, 60)
    assert corrected < raw


def test_high_sigma_passes_bonferroni_with_many_tests() -> None:
    passes, _, _ = passes_bonferroni(80.0, 60)
    assert passes


def test_low_sigma_fails_bonferroni() -> None:
    passes, _, _ = passes_bonferroni(1.0, 100)
    assert not passes


def test_sigma_p_roundtrip() -> None:
    p = sigma_to_two_sided_p(3.0)
    assert 0.0 < p < 0.01
