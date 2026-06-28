"""Unit tests for Fokker-Planck inflation step."""

import numpy as np

from polomni.core.inflation.fokker_planck import fokker_planck_step, radon_modified_D_eff


def test_radon_modified_D_eff_base_term() -> None:
    h = 1.0
    d = radon_modified_D_eff(h, stream_fluxes=np.array([]), lambda_coupling=1.0)
    assert d == pytest.approx(1.0 / (8.0 * np.pi**2), rel=1e-9)


def test_radon_modified_D_eff_stream_adds() -> None:
    base = radon_modified_D_eff(1.0, np.array([]), 1.0)
    boosted = radon_modified_D_eff(1.0, np.array([1.0]), 1.0)
    assert boosted == pytest.approx(base + 1.0, rel=1e-9)


def test_fokker_planck_preserves_normalization_approximately() -> None:
    phi = np.linspace(-2, 2, 51)
    p = np.exp(-phi**2)
    p /= np.trapz(p, phi)
    v = 0.5 * phi**2
    h = np.full_like(phi, 1.0)
    d_eff = 0.01
    p_next = fokker_planck_step(p, phi, v, h, dt=0.001, d_eff=d_eff)
    assert np.all(p_next >= -1e-6)
    integral = np.trapz(p_next, phi)
    assert integral == pytest.approx(1.0, rel=0.1)


import pytest  # noqa: E402
