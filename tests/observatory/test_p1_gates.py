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


def _gate_payload(mode: str, blind: bool) -> dict:
    return {
        "mode": mode,
        "blind": blind,
        "map_product_id": "planck_smica_cmb" if blind else "wmap_k_band",
        "null_tier_comparison": {
            "tiers": {"N0": {}, "N1": {}, "N2": {}},
        },
        "detection": {"rble_score": 1.0},
        "p1_supported": False,
        "p1_falsified": blind,
        "ran_at": "2026-08-16T12:00:00+00:00",
        "git_sha": "eee86c9",
    }


def test_gate4_ignores_calibration_result(monkeypatch, tmp_path) -> None:
    from polomni.observatory.studies.gates import check_gate4_blind_holdout
    from polomni.observatory.studies.results import publish_result

    monkeypatch.chdir(tmp_path)
    publish_result(_gate_payload("calibration", False), mode="calibration")

    check = check_gate4_blind_holdout()

    assert check.passed is False
    assert "No RESULT.json" in check.message


def test_gate4_reads_only_canonical_blind_result(monkeypatch, tmp_path) -> None:
    from polomni.observatory.studies.gates import check_gate4_blind_holdout
    from polomni.observatory.studies.results import publish_result

    monkeypatch.chdir(tmp_path)
    publish_result(_gate_payload("exploratory", False), mode="exploratory")
    publish_result(_gate_payload("holdout_blind", True), mode="holdout_blind")

    check = check_gate4_blind_holdout()

    assert check.passed is True
    assert check.details["git_sha"] == "eee86c9"


def test_gate4_handles_missing_canonical_result(monkeypatch, tmp_path) -> None:
    from polomni.observatory.studies.gates import check_gate4_blind_holdout

    monkeypatch.chdir(tmp_path)

    check = check_gate4_blind_holdout()

    assert check.passed is False
    assert "No RESULT.json" in check.message
