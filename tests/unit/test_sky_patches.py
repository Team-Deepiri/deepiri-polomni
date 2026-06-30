"""Unit tests for D_eff sky patches and f_NL proxy."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.inflation.sky_patches import estimate_local_fnl_proxy, map_deff_to_sky_patches
from polomni.core.state.stream_packet import StreamPacket
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.core.inflation.sky_patches import deff_fnl_from_simulation


def _packet() -> StreamPacket:
    return StreamPacket(
        district_id=1,
        parent_id=0,
        num_choices=3,
        phi_stream=[0.5, 0.3, 0.2],
        information_trace=0.1,
        branch_weights=[0.5, 0.3, 0.2],
    )


def test_map_deff_has_variation() -> None:
    axes = [np.array([0, 0, 1.0]), np.array([0.1, 0.2, 0.97])]
    deff = map_deff_to_sky_patches([_packet(), _packet()], axes, nside=8)
    assert deff.size == 12 * 8 * 8
    assert float(np.std(deff)) > 0.0


def test_fnl_proxy_normalized() -> None:
    deff = np.linspace(0, 1, 96)
    fnl = estimate_local_fnl_proxy(deff, patch_size=48)
    assert float(np.std(fnl)) > 0.5


def test_deff_fnl_from_simulation() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    packets = graph.trigger_choice_event(root, 3)
    out = deff_fnl_from_simulation(graph, packets, nside=8)
    assert "fnl_proxy" in out
    assert out["mean_deff"] > 0.0
