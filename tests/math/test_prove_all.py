"""Tests for RBLE math proof suite."""

from polomni.math import prove_all


def test_prove_all_passes() -> None:
    suite = prove_all(save=False)
    assert len(suite.results) >= 12
    assert suite.passed_count >= 10
    assert suite.all_passed


def test_prove_strict_passes_without_real_data() -> None:
    suite = prove_all(save=False, strict=True, real_data=False)
    assert len(suite.results) >= 17
    assert suite.all_passed
