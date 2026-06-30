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
