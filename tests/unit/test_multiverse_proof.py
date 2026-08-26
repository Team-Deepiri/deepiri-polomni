"""Tests for multiverse computational proof runner."""

from __future__ import annotations

from polomni.integration.multiverse_proof import run_multiverse_proof


def test_multiverse_proof_quick() -> None:
    report = run_multiverse_proof(quick=True, injection_trials=5, loop_steps=2)
    assert report.mode == "quick"
    assert len(report.metrics) >= 5
    assert report.elapsed_seconds > 0.0
    ids = {m.id for m in report.metrics}
    assert "M2_injection_recovery" in ids
    assert "M3_closed_loop" in ids
    assert "M4_branch_entropy" in ids
    payload = report.to_dict()
    assert "multiverse_branching" in payload
    assert report.pass_rate > 0.5
    assert report.computational_passed


def test_multiverse_proof_real_sky_cached() -> None:
    """Operational proof when cached M2 + scar JSON exist (CI may skip if missing)."""
    from pathlib import Path

    scar = Path("data/reports/multi_survey_scar_consensus.json")
    m2 = Path("data/reports/m2_neural_real_sky_probe.json")
    if not scar.is_file() or not m2.is_file():
        return
    report = run_multiverse_proof(quick=True, include_real_sky=True)
    assert "M8_multi_survey_scar" in {m.id for m in report.metrics}
    assert "M9_neural_real_sky" in {m.id for m in report.metrics}
    if report.real_sky_passed:
        assert report.multiverse_proof_operational
        if report.instrument_proven:
            assert report.multiverse_works
            assert report.evidence_tier == "multiverse_works"
        else:
            assert report.evidence_tier == "multiverse_proof_operational"
