"""Tests for multi-survey scar consensus instrument."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.multi_survey_scar import (
    consensus_axis,
    density_map_from_vectors,
    pairwise_max_sep_deg,
    residual_nematic_axis,
    score_axis_vs_footprint_null,
)


def test_consensus_axis_antipodal_alignment() -> None:
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([-1.0, 0.05, 0.0])  # nearly antipodal
    c = consensus_axis([a, b])
    assert abs(float(np.linalg.norm(c)) - 1.0) < 1e-9
    # After flip, both should pull toward +x
    assert c[0] > 0.9


def test_pairwise_max_sep_close_axes() -> None:
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.98, 0.2, 0.0])
    b = b / np.linalg.norm(b)
    assert pairwise_max_sep_deg([a, b]) < 15.0


def test_residual_nematic_orthogonal_to_footprint() -> None:
    rng = np.random.default_rng(0)
    # Cluster along z (footprint) plus a weaker x preference
    foot = np.tile([0.0, 0.0, 1.0], (200, 1))
    scar = np.tile([1.0, 0.0, 0.0], (40, 1))
    noise = rng.normal(size=(40, 3))
    noise /= np.linalg.norm(noise, axis=1, keepdims=True)
    vecs = np.vstack([foot, 0.7 * scar + 0.3 * noise])
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    dipole = vecs.mean(axis=0)
    dipole /= np.linalg.norm(dipole)
    resid = residual_nematic_axis(vecs, dipole)
    # Residual should not collapse onto the footprint pole
    sep = float(np.degrees(np.arccos(np.clip(abs(np.dot(resid, dipole)), -1, 1))))
    assert sep > 5.0


def test_score_axis_vs_null_smoke() -> None:
    rng = np.random.default_rng(1)
    nside = 8
    # Synthetic density peaked along +x
    import healpy as hp

    npix = hp.nside2npix(nside)
    dens = np.zeros(npix)
    dens[hp.vec2pix(nside, 1.0, 0.0, 0.0)] = 1.0
    dens[hp.vec2pix(nside, 0.9, 0.1, 0.0)] = 0.8
    axis = np.array([1.0, 0.0, 0.0])
    nulls = [rng.random(npix) for _ in range(5)]
    for m in nulls:
        m /= m.max()
    out = score_axis_vs_footprint_null(dens, axis, null_maps=nulls)
    assert "null_sigma" in out
    assert out["s_rble"] >= 0.0


def test_density_map_from_vectors_shape() -> None:
    import healpy as hp

    nside = 8
    vecs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    m = density_map_from_vectors(vecs, nside)
    assert m.shape == (hp.nside2npix(nside),)
    assert abs(float(m.max()) - 1.0) < 1e-9


def test_joint_ring_finds_planted_axis() -> None:
    from polomni.observatory.pipeline.sources.multi_survey_scar import joint_ring_axis_search

    rng = np.random.default_rng(2)
    true = np.array([0.0, 0.0, 1.0])
    # Objects concentrated near equator of +z
    n = 300
    phi = rng.uniform(0, 2 * np.pi, n)
    # lat near 0 → z small
    z = rng.normal(0, 0.08, n)
    rxy = np.sqrt(np.clip(1 - z * z, 0, 1))
    vecs = np.column_stack([rxy * np.cos(phi), rxy * np.sin(phi), z])
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    # Second sky same ring + noise
    vecs2 = vecs.copy()
    vecs2 += rng.normal(0, 0.02, vecs2.shape)
    vecs2 /= np.linalg.norm(vecs2, axis=1, keepdims=True)
    out = joint_ring_axis_search(
        {"a": vecs, "b": vecs2},
        cmb_consensus=true,
        dir_nside=4,
        n_null=32,
        seed=0,
    )
    assert out["found"]
    assert out["min_null_sigma"] > 1.0
    assert out["sep_from_cmb_consensus_deg"] < 25.0
