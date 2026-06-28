"""Tests for RBLE math proof suite."""

from polomni.math import prove_all


def test_prove_all_passes() -> None:
    suite = prove_all(save=False)
    assert len(suite.results) >= 12
    assert suite.passed_count >= 10
    assert suite.all_passed
