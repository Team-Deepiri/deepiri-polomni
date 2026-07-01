"""Tests for P1 gate checks."""

from polomni.observatory.studies.gates import run_p1_gates


def test_p1_gates_run() -> None:
    report = run_p1_gates(injection_trials=8)
    assert len(report.checks) == 3
    assert report.checks[0].gate == "G1"
    assert report.checks[0].passed


def test_p1_gate4_when_result_exists() -> None:
    from pathlib import Path

    if not Path("data/studies/p1_holdout/RESULT.json").is_file():
        return
    from polomni.observatory.studies.gates import run_p1_gates_full

    report = run_p1_gates_full(injection_trials=4, require_blind=True)
    assert len(report.checks) == 4
    assert report.checks[3].gate == "G4"
