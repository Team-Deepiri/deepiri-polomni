"""Tests for the bubble-collision search instrument."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.pipeline.sources.bubble_collisions import (
    bubble_scan_geometry,
    circle_edge_statistic,
    galactic_edge_mask,
    harmonic_axis_search,
    inject_bubble_collision,
    load_planck_for_search,
    scan_circle_edges,
)


@pytest.fixture(scope="module")
def geometry() -> tuple[list, np.ndarray]:
    return bubble_scan_geometry(nside=64, nside_dir=4)


def test_galactic_edge_mask_covers_expected_fraction() -> None:
    mask = galactic_edge_mask(64, b_cut=20.0)
    assert mask.dtype == bool
    f_sky = float(np.mean(mask))
    # |b| >= 20° covers ~66% of the sky; the double-rotation bug would put
    # the strip in the wrong place (f_sky would be wrong by a large margin).
    assert 0.5 < f_sky < 0.8
    assert mask.shape == (12 * 64 * 64,)


def test_geometry_rings_respect_mask(geometry) -> None:
    geoms, mask = geometry
    assert len(geoms) > 50
    for g in geoms[:20]:
        # every stored pixel must be unmasked
        assert np.all(mask[g.inner_pix])
        assert np.all(mask[g.outer_pix])
        # rings must be non-empty
        assert g.inner_pix.size >= 4
        assert g.outer_pix.size >= 4


def test_edge_statistic_flat_map_zero() -> None:
    import healpy as hp

    geoms, _ = bubble_scan_geometry(nside=32, nside_dir=4)
    t = np.full(hp.nside2npix(32), 100.0)
    edges = scan_circle_edges(t, geoms)
    assert np.allclose(edges, 0.0, atol=1e-6)


def test_injection_recovery_exact() -> None:
    import healpy as hp

    geoms, _ = bubble_scan_geometry(nside=64, nside_dir=4)
    c = geoms[3]
    center = np.stack(hp.pix2vec(64, int(hp.ang2pix(64, c.theta_rad, c.phi_rad))), axis=0)
    t = np.zeros(hp.nside2npix(64))
    planted = inject_bubble_collision(t, center, c.radius_deg, 300.0, 64)
    edges = scan_circle_edges(planted, geoms)
    order = np.argsort(-np.abs(edges))
    best = geoms[int(order[0])]
    assert best.radius_deg == c.radius_deg
    assert abs(best.theta_rad - c.theta_rad) < 1e-6
    assert edges[int(order[0])] < -100.0  # outside is colder than inside


def test_injection_edge_amplitude_scales_with_step() -> None:
    import healpy as hp

    geoms, _ = bubble_scan_geometry(nside=64, nside_dir=4)
    c = geoms[1]
    center = np.stack(hp.pix2vec(64, int(hp.ang2pix(64, c.theta_rad, c.phi_rad))), axis=0)
    t = np.zeros(hp.nside2npix(64))
    edges_200 = scan_circle_edges(
        inject_bubble_collision(t, center, c.radius_deg, 200.0, 64), geoms
    )
    edges_400 = scan_circle_edges(
        inject_bubble_collision(t, center, c.radius_deg, 400.0, 64), geoms
    )
    # strongest edge roughly doubles with the injected amplitude
    e200 = float(np.max(np.abs(edges_200)))
    e400 = float(np.max(np.abs(edges_400)))
    assert e400 / e200 > 1.7


def test_mask_edge_circles_excluded() -> None:
    geoms, mask = bubble_scan_geometry(nside=64, nside_dir=4, b_cut=20.0)
    import healpy as hp

    for g in geoms:
        # no candidate ring may straddle the Galactic cut
        theta, _ = hp.pix2ang(64, g.inner_pix)
        b_min = float(np.min(np.abs(90.0 - np.degrees(theta))))
        assert b_min >= 19.0


def test_rank1_pure_disk_axis_recovered() -> None:
    import healpy as hp

    nside = 64
    npix = hp.nside2npix(nside)
    t = np.zeros(npix)
    nc = np.array([0.6, 0.8, 0.2])
    nc = nc / np.linalg.norm(nc)
    t = inject_bubble_collision(t, nc, 40.0, 1000.0, nside)
    res = harmonic_axis_search(t, nside, lmax=20, nside_dir=8, n_null=4)
    th_r = np.radians(90.0 - res["axis"]["gal_lat"])
    ph_r = np.radians(res["axis"]["gal_lon"])
    nr = np.array(
        [np.sin(th_r) * np.cos(ph_r), np.sin(th_r) * np.sin(ph_r), np.cos(th_r)]
    )
    err = np.degrees(np.arccos(np.clip(nr @ nc, -1, 1)))
    # a pure axisymmetric disk is exactly rank-1: the axis must come out on top
    assert err < 5.0
    assert res["score"] > 0.1


def test_rank1_collision_over_null_on_planck() -> None:
    t, _pid = load_planck_for_search(nside=64)
    nc = np.array([0.6, 0.8, 0.2])
    nc = nc / np.linalg.norm(nc)
    injected = inject_bubble_collision(t, nc, 40.0, 1500.0, 64)
    res = harmonic_axis_search(injected, 64, lmax=20, nside_dir=8, n_null=16)
    # the injected collision must beat the C_ℓ-matched null
    assert res["p_value"] < 0.2
    assert res["score"] > res["null"]["max_score_median"]


def test_rank1_planck_no_false_detection() -> None:
    t, _pid = load_planck_for_search(nside=64)
    res = harmonic_axis_search(t, 64, lmax=20, nside_dir=4, n_null=12)
    # the CMB's own "axis of evil" must NOT be reported as a collision
    assert res["p_value"] > 0.1
