"""Tests for baseline tolerance tables."""

from polomni.math.proofs.baselines import check_metric, check_within, load_tolerance_table


def test_tolerance_table_loads() -> None:
    table = load_tolerance_table()
    assert "eq04" in table
    assert table["eq04"]["atol"] <= 1e-5


def test_check_within_passes_expected() -> None:
    passed, residual, _ = check_within("eq04", {"closure_residual": 1e-8})
    assert passed
    assert residual < 1e-6


def test_check_metric_fails_above_max() -> None:
    check = check_metric("eq04", "closure_residual", 1.0, section="metrics")
    assert not check.passed
