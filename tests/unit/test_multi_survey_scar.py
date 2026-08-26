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


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float).ravel()
    return v / (np.linalg.norm(v) + 1e-15)


def _plant_polar_catalog(axis: np.ndarray, n: int, frac: float, rng: np.random.Generator) -> np.ndarray:
    """Isotropic catalog with a planted polar concentration along *axis*."""
    axis = _unit(axis)
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    n_plant = int(frac * n)
    tmp = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    x = _unit(np.cross(axis, tmp))
    y = _unit(np.cross(axis, x))
    sign = np.where(rng.random(n_plant) < 0.5, 1.0, -1.0)
    mu = sign * (0.92 + 0.08 * rng.random(n_plant))
    phi = rng.uniform(0, 2 * np.pi, n_plant)
    s = np.sqrt(np.maximum(1.0 - mu * mu, 0.0))
    v[:n_plant] = (
        mu[:, None] * axis
        + (s * np.cos(phi))[:, None] * x
        + (s * np.sin(phi))[:, None] * y
    )
    return v


def test_polar_sigma_recovers_planted_axis_away_from_pole() -> None:
    """Polar null recovers a planted scar at moderate latitude (free-sky null)."""
    from polomni.observatory.pipeline.sources.multi_survey_scar import polar_sigma_at_axis
    import healpy as hp

    rng = np.random.default_rng(11)
    axis = _unit(np.asarray(hp.ang2vec(250.0, 45.0, lonlat=True), dtype=float).ravel())
    vecs = _plant_polar_catalog(axis, n=6000, frac=0.50, rng=rng)
    out = polar_sigma_at_axis(vecs, axis, n_null=150, rng=rng, lat_matched=False)
    wrong = polar_sigma_at_axis(
        vecs, _unit(np.array([0.0, 1.0, 0.0])), n_null=150, rng=rng, lat_matched=False
    )
    assert out["null_sigma"] >= 2.0
    assert wrong["null_sigma"] < out["null_sigma"]


def test_lat_matched_polar_null_blocks_pole_artifact() -> None:
    """Isotropic+|b| cut must not clear lat-matched polar at a near-GNP axis."""
    from polomni.observatory.pipeline.sources.cmb_mask import galactic_latitude_cut
    from polomni.observatory.pipeline.sources.multi_survey_scar import polar_sigma_at_axis
    import healpy as hp

    rng = np.random.default_rng(4)
    axis = _unit(np.asarray(hp.ang2vec(108.0, 85.0, lonlat=True), dtype=float).ravel())
    v = rng.normal(size=(12000, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    v = v[galactic_latitude_cut(v, 20.0)]
    free = polar_sigma_at_axis(v, axis, n_null=100, rng=rng, lat_matched=False)
    matched = polar_sigma_at_axis(v, axis, n_null=100, rng=rng, lat_matched=True)
    # Free null can look spuriously high near GNP; lat-matched must stay mild.
    assert matched["null_sigma"] < 2.0
    assert matched["null_sigma"] <= free["null_sigma"] + 0.5


def _plant_residual_catalog(
    scar_axis: np.ndarray,
    footprint_axis: np.ndarray,
    n: int,
    rng: np.random.Generator,
    *,
    scar_frac: float = 0.35,
) -> np.ndarray:
    """Footprint dipole along *footprint_axis* + scar preference along *scar_axis*."""
    scar_axis = _unit(scar_axis)
    footprint_axis = _unit(footprint_axis)
    n_scar = int(scar_frac * n)
    n_foot = n - n_scar
    foot = np.tile(footprint_axis, (n_foot, 1)) + rng.normal(0, 0.15, (n_foot, 3))
    foot /= np.linalg.norm(foot, axis=1, keepdims=True)
    scar = np.tile(scar_axis, (n_scar, 1)) + rng.normal(0, 0.20, (n_scar, 3))
    scar /= np.linalg.norm(scar, axis=1, keepdims=True)
    v = np.vstack([foot, scar])
    rng.shuffle(v)
    return v


def test_residual_consensus_recovers_planted_shared_axis() -> None:
    """Several catalogs sharing a planted residual direction beat isotropic null."""
    from polomni.observatory.pipeline.sources.multi_survey_scar import (
        catalog_residual_consensus_null,
    )
    import healpy as hp

    rng = np.random.default_rng(21)
    planted = _unit(np.asarray(hp.ang2vec(120.0, 70.0, lonlat=True), dtype=float).ravel())
    # Footprint orthogonal-ish to planted so residual recovers the scar.
    foot = _unit(np.asarray(hp.ang2vec(30.0, -10.0, lonlat=True), dtype=float).ravel())
    catalogs = {
        "a": _plant_residual_catalog(planted, foot, n=2000, rng=rng),
        "b": _plant_residual_catalog(planted, foot, n=1500, rng=rng),
        "c": _plant_residual_catalog(planted, foot, n=1200, rng=rng),
        "d": _plant_residual_catalog(planted, foot, n=1800, rng=rng),
    }
    out = catalog_residual_consensus_null(
        catalogs,
        planted,
        b_cut_by_sky={k: None for k in catalogs},
        n_null=80,
        seed=0,
    )
    assert out["gate_pass"] is True
    assert out["p_joint_consensus_and_pairwise"] <= 0.05
    assert out["consensus_sep_from_cmb_deg"] < 30.0


def test_residual_consensus_isotropic_does_not_pass() -> None:
    from polomni.observatory.pipeline.sources.multi_survey_scar import (
        catalog_residual_consensus_null,
    )
    import healpy as hp

    rng = np.random.default_rng(33)
    cmb = _unit(np.asarray(hp.ang2vec(108.0, 85.0, lonlat=True), dtype=float).ravel())
    catalogs = {
        "a": rng.normal(size=(2000, 3)),
        "b": rng.normal(size=(1500, 3)),
        "c": rng.normal(size=(1200, 3)),
    }
    for v in catalogs.values():
        v /= np.linalg.norm(v, axis=1, keepdims=True)
    out = catalog_residual_consensus_null(
        catalogs,
        cmb,
        b_cut_by_sky={k: None for k in catalogs},
        n_null=60,
        seed=1,
    )
    # Pure isotropic should not systematically clear the joint gate.
    assert out["p_joint_consensus_and_pairwise"] > 0.02
