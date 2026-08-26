"""Tests for neural real-sky multiverse probe helpers."""

from __future__ import annotations

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.real_sky_bridge import align_sim_to_real, run_physics_loop
from polomni.neural.multiverse_probe import ArmProbe, MultiverseProbeReport


def test_align_sim_to_real_antipode_safe():
    a = [0.0, 0.0, 1.0]
    b = [0.0, 0.0, -1.0]
    out = align_sim_to_real(a, b)
    assert out["separation_deg"] < 1e-5  # undirected axes
    assert out["alignment_quality"] > 0.99


def test_probe_report_roundtrip():
    report = MultiverseProbeReport(
        map_product_id="wmap_k_band",
        nside=16,
        steps=2,
        real_axis=[0.0, 0.0, 1.0],
        real_score=1.0,
        arms={
            "uniform": ArmProbe("uniform", 10.0, 12.0, 0.9, 0.8, 1.0),
            "neural": ArmProbe("neural", 5.0, 6.0, 0.95, 0.9, 1.0),
        },
        neural_beats_uniform=True,
        improvement_deg=5.0,
        claim="test",
    )
    d = report.to_dict()
    assert d["study_id"] == "m2_neural_real_sky_probe"
    assert d["arms"]["neural"]["final_separation_deg"] == 5.0


def test_physics_loop_accepts_neural_policy_synthetic_path(monkeypatch):
    """Smoke: neural policy path constructs without requiring real FITS if mocked."""
    import numpy as np
    import polomni.integration.real_sky_bridge as bridge

    fake_axis = np.array([0.1, 0.2, 0.97], dtype=float)
    fake_axis /= np.linalg.norm(fake_axis)
    fake = bridge.PreferredAxisMeasurement(
        map_product_id="wmap_k_band",
        nside=16,
        axis=fake_axis.tolist(),
        rble_score=42.0,
        lon_deg=0.0,
        lat_deg=0.0,
        source_path="/tmp/fake.fits",
    )

    monkeypatch.setattr(bridge, "measure_preferred_axis", lambda *a, **k: fake)
    result = run_physics_loop(
        steps=1,
        nside=16,
        seed=0,
        policy=ChoicePolicy.NEURAL,
        neural_prescreen_real=False,
    )
    assert len(result.steps) == 1
    assert result.real_score == 42.0
    assert result.preferred_axis is not None
    assert result.preferred_axis.source_path == "/tmp/fake.fits"
