"""Tests for P5-RDF tomography proxy."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask
from polomni.observatory.pipeline.sources.rdf_tomography import (
    axis_separation_deg,
    bubble_template_coherence,
    galaxy_overdensity_map,
    inject_bubble_rdf_signal,
    multipole_weighted_cross,
    rble_scar_axis_test,
    scores_at_axis,
    search_bubble_template_axis,
    search_rdf_rqf,
    shuffle_galaxy_positions,
)
from polomni.observatory.pipeline.sources.bubble_collision_template import bubble_template_score


@pytest.fixture
def sky_setup():
    import healpy as hp

    nside = 32
    npix = hp.nside2npix(nside)
    mask = galactic_edge_mask(nside, b_cut=20.0)
    cmb = np.random.default_rng(0).normal(0, 10.0, npix)
    cmb[~mask] = 0.0
    rng = np.random.default_rng(1)
    n_gal = 400
    vecs = hp.pix2vec(nside, rng.choice(np.where(mask)[0], size=n_gal, replace=True))
    vecs = np.column_stack(vecs)
    delta = galaxy_overdensity_map(vecs, nside, mask)
    return nside, mask, cmb, delta, vecs


def test_multipole_cross_flat_galaxy_near_zero(sky_setup) -> None:
    nside, mask, cmb, delta, _ = sky_setup
    import healpy as hp

    axis = np.array([0.0, 0.0, 1.0])
    s1 = multipole_weighted_cross(cmb, delta, axis, ell=1, mask=mask)
    s2 = multipole_weighted_cross(cmb, delta, axis, ell=2, mask=mask)
    assert abs(s1) < 50.0
    assert abs(s2) < 50.0
    assert hp.get_nside(cmb) == nside


def test_injection_recovers_axis(sky_setup) -> None:
    nside, mask, cmb, delta, _ = sky_setup
    true_axis = np.array([0.3, 0.2, 0.9])
    true_axis /= np.linalg.norm(true_axis)
    t_inj, d_inj = inject_bubble_rdf_signal(
        cmb, delta, true_axis, rdf_amp=80.0, rqf_amp=60.0, mask=mask
    )
    res = search_rdf_rqf(t_inj, d_inj, mask=mask, nside_dir=16)
    sep_rdf = axis_separation_deg(res.rdf_axis, true_axis)
    sep_rqf = axis_separation_deg(res.rqf_axis, true_axis)
    assert sep_rdf < 25.0
    assert sep_rqf < 25.0
    assert res.axis_separation_deg < 15.0


def test_shuffle_preserves_count(sky_setup) -> None:
    _, mask, _, _, vecs = sky_setup
    import healpy as hp

    nside = hp.get_nside(mask)
    rng = np.random.default_rng(42)
    shuf = shuffle_galaxy_positions(vecs, nside, mask, rng)
    assert shuf.shape == vecs.shape


def test_bubble_template_coherent_sign() -> None:
    assert bubble_template_score(2.0, 3.0) > bubble_template_score(2.0, -3.0)


def test_phase_b_recovers_injected_axis(sky_setup) -> None:
    nside, mask, cmb, delta, _ = sky_setup
    true_axis = np.array([0.2, -0.1, 0.97])
    true_axis /= np.linalg.norm(true_axis)
    t_inj, d_inj = inject_bubble_rdf_signal(
        cmb, delta, true_axis, rdf_amp=100.0, rqf_amp=80.0, mask=mask
    )
    axis, score, _, _, _ = search_bubble_template_axis(t_inj, d_inj, mask=mask, nside_dir=16)
    assert axis_separation_deg(axis, true_axis) < 20.0
    assert score > 0.5


def test_rble_scar_axis_enhancement_on_injection(sky_setup) -> None:
    nside, mask, cmb, delta, _ = sky_setup
    scar = np.array([0.1, 0.05, 0.99])
    scar /= np.linalg.norm(scar)
    t_inj, d_inj = inject_bubble_rdf_signal(
        cmb, delta, scar, rdf_amp=120.0, rqf_amp=90.0, mask=mask
    )
    result = rble_scar_axis_test(t_inj, d_inj, scar, mask=mask, n_null=32, seed=0)
    assert result["gate_pass"] is True
    assert result["null"]["p_value"] <= 0.05


def test_rble_physics_chain_validation() -> None:
    from polomni.observatory.pipeline.sources.rdf_tomography import rble_model_physics_validation

    result = rble_model_physics_validation(nside=32, seed=7, rdf_amp=150.0, rqf_amp=100.0)
    assert result["gate_pass"] is True
    assert result["axis_error_deg"] < 20.0
    axis = np.array([0.1, 0.2, 0.97])
    sep_a, coh_a = bubble_template_coherence(axis, axis, rdf_score=2.0, rqf_score=3.0)
    orth = np.array([0.97, 0.2, -0.1])
    orth /= np.linalg.norm(orth)
    sep_b, coh_b = bubble_template_coherence(axis, orth, rdf_score=2.0, rqf_score=3.0)
    assert sep_a < sep_b
    assert coh_a > coh_b
