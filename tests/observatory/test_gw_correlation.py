"""Unit tests for GW–RBLE axis correlation stub."""

import numpy as np
import pytest

from polomni.observatory.pipeline.processor import correlate_gw_rble
from polomni.observatory.pipeline.sources.gwosc import GWEvent


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("healpy") is None,
    reason="healpy required",
)
def test_correlate_gw_rble_finds_nearby_event() -> None:
    preferred = [0.0, 0.0, 1.0]
    nearby = GWEvent(
        name="GW_TEST_NEAR",
        gps=0.0,
        catalog="GWTC",
        detectors=["H1"],
        network_axis=[0.0, 0.0, 1.0],
    )
    far = GWEvent(
        name="GW_TEST_FAR",
        gps=0.0,
        catalog="GWTC",
        detectors=["H1"],
        network_axis=[1.0, 0.0, 0.0],
    )

    matches = correlate_gw_rble(preferred, [nearby, far], max_separation_deg=30.0)
    names = {m["name"] for m in matches}
    assert "GW_TEST_NEAR" in names
    assert "GW_TEST_FAR" not in names
    assert matches[0]["separation_deg"] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("healpy") is None,
    reason="healpy required",
)
def test_correlate_gw_rble_uses_detector_network_axis() -> None:
    preferred = np.array([0.954, -0.257, 0.151])
    preferred = preferred / np.linalg.norm(preferred)

    event = GWEvent(
        name="GW_H1_ONLY",
        gps=0.0,
        catalog="GWTC",
        detectors=["H1"],
    )
    matches = correlate_gw_rble(preferred.tolist(), [event], max_separation_deg=30.0)
    assert len(matches) == 1
    assert matches[0]["name"] == "GW_H1_ONLY"


def test_correlate_gw_rble_skips_events_without_axis() -> None:
    event = GWEvent(name="GW_EMPTY", gps=0.0, catalog="GWTC", detectors=[])
    matches = correlate_gw_rble([0.0, 0.0, 1.0], [event])
    assert matches == []
