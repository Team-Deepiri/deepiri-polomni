"""Tests for end-to-end multiverse instrument proof (M15)."""

from __future__ import annotations

from polomni.integration.multiverse_instrument_proof import multiverse_instrument_proof


def test_instrument_holdout_recovers_shared_bubble() -> None:
    result = multiverse_instrument_proof(
        nside=32, seed=7, nside_dir=4, n_null=4, rdf_amp=220.0, rqf_amp=160.0
    )
    assert result["gate_pass"] is True
    assert result["train"]["axis_error_deg"] < 30.0
    assert result["holdout"]["fisher_snr_at_frozen"] > 0.35
