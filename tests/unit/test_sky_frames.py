"""Tests for equatorial ↔ Galactic frame rotation."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.sky_frames import (
    equatorial_to_galactic,
    galactic_to_equatorial,
    rotate_sky_vectors,
)


def test_roundtrip_equatorial_galactic() -> None:
    rng = np.random.default_rng(0)
    v = rng.normal(size=(20, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    g = equatorial_to_galactic(v)
    back = galactic_to_equatorial(g)
    assert np.allclose(np.abs(np.sum(v * back, axis=1)), 1.0, atol=1e-5)


def test_galactic_north_pole_known() -> None:
    # Equatorial RA/Dec of Galactic north pole ≈ (192.8595, 27.1283)
    ra, dec = np.radians(192.8595), np.radians(27.1283)
    equ = np.array(
        [np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)]
    )
    gal = equatorial_to_galactic(equ)
    # Should land near +z in Galactic
    assert gal[2] > 0.99


def test_identity_same_frame() -> None:
    v = np.array([0.0, 1.0, 0.0])
    out = rotate_sky_vectors(v, from_frame="galactic", to_frame="galactic")
    assert np.allclose(out, v)
