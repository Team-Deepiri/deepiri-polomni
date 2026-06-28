"""Unit tests for RadonVacuumPipeline."""

import numpy as np

from omnifold_core.conservation import compute_information_trace, stream_flux_integral
from omnifold_core.gravity.information_tensor import information_tensor_N
from omnifold_core.radon.vacuum_stream import RadonVacuumPipeline


def test_vacuum_pipeline_conservation_closure() -> None:
    nx = 11
    coords = np.linspace(-2, 2, nx)
    xg, yg, zg = np.meshgrid(coords, coords, coords, indexing="ij")
    psi = np.exp(-(xg**2 + yg**2 + zg**2))

    pipe = RadonVacuumPipeline(
        district_id=1,
        num_choices=5,
        horizon_area=4.0 * np.pi,
        rotation_angles=(0.1, 0.2, 0.3),
        entropy_gradient=np.array([0.1, 0.2, 0.3, 0.4]),
    )
    packet = pipe.run(psi)
    grad = np.array([0.1, 0.2, 0.3, 0.4])
    i_tensor = information_tensor_N(5, grad)
    expected_trace = compute_information_trace(i_tensor)
    assert packet.information_trace == pytest.approx(expected_trace, rel=1e-5)
    flux = stream_flux_integral(packet.phi_array(), pipe.horizon_area)
    assert flux == pytest.approx(expected_trace, rel=1e-5)


def test_stream_packet_fields() -> None:
    pipe = RadonVacuumPipeline(district_id=0, parent_id=None, num_choices=3)
    psi = np.zeros((5, 5, 5))
    psi[2, 2, 2] = 1.0
    packet = pipe.run(psi)
    assert packet.district_id == 0
    assert packet.num_choices == 3
    assert len(packet.phi_stream) == packet.num_choices


import pytest  # noqa: E402
