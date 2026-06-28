"""Tests for P1 gate checks."""

from polomni.observatory.studies.gates import run_p1_gates


def test_p1_gates_run() -> None:
    report = run_p1_gates(injection_trials=8)
    assert len(report.checks) == 3
    assert report.checks[0].gate == "G1"
    assert report.checks[0].passed
