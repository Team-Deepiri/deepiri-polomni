"""Unit tests for Kähler landscape potential."""

import numpy as np

from omnifold_core.landscape.kahler import kahler_total, modulus_stabilization_rate


def test_kahler_volume_term() -> None:
    t = 1.0 + 0.0j
    k = kahler_total(t, i_trace=0.0, phi_stream_flux=0.0, beta=0.0, gamma=0.0, m_planck=1.0)
    # -3 ln(2) for T = T̄ = 1
    assert k == pytest.approx(-3.0 * np.log(2.0), rel=1e-9)


def test_kahler_information_backreaction() -> None:
    k0 = kahler_total(1.0, i_trace=0.0, phi_stream_flux=0.0, beta=1.0, gamma=0.0)
    k1 = kahler_total(1.0, i_trace=2.0, phi_stream_flux=0.0, beta=1.0, gamma=0.0)
    assert k1 - k0 == pytest.approx(2.0, rel=1e-9)


def test_modulus_stabilization_rate_sign() -> None:
    rate = modulus_stabilization_rate(
        t=1.0,
        d_i_trace_dt=3.0,
        d_flux_dt=0.0,
        beta=1.0,
        m_planck=1.0,
    )
    assert rate == pytest.approx(-1.0, rel=1e-9)


import pytest  # noqa: E402
