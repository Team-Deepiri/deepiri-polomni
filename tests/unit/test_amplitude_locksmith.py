"""Unit tests for Phase J amplitude locksmith (matched-filter past Pearson)."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.amplitude_locksmith import (
    matched_fisher_snr,
    matched_mode_snr,
    MatchedM0,
)


def test_matched_mode_snr_perfect_alignment() -> None:
    rng = np.random.default_rng(0)
    template = np.linspace(-1.0, 1.0, 200)
    field = 3.0 * template + 0.01 * rng.normal(size=template.shape)
    snr = matched_mode_snr(field, template)
    assert snr > 5.0


def test_matched_fisher_combines_modes() -> None:
    amps = MatchedM0(a10=4.0, a20=2.6, axis=np.array([0.0, 0.0, 1.0]), sign_coherent=True)
    snr = matched_fisher_snr(amps, A=1.0, B=0.65)
    # Projection onto unit template should exceed either mode alone in template units
    assert snr > 4.0


def test_inject_ladder_reaches_gate() -> None:
    """Synthetic sky: large inject at z-axis must prove amplitude path."""
    import healpy as hp

    from polomni.observatory.pipeline.sources.amplitude_locksmith import (
        inject_amplitude_ladder,
    )

    nside = 8
    npix = hp.nside2npix(nside)
    rng = np.random.default_rng(1)
    cmb = rng.normal(size=npix)
    delta = rng.normal(size=npix)
    mask = np.ones(npix, dtype=bool)
    axis = np.array([0.0, 0.0, 1.0])
    ladder = inject_amplitude_ladder(
        cmb,
        delta,
        mask,
        axis,
        amplitudes=(4.0, 16.0, 48.0),
        n_null=24,
        seed=0,
    )
    assert ladder["amplitude_path_proven"] is True
    assert ladder["min_amp_gate_pass"] is not None
    assert ladder["min_amp_gate_pass"] <= 48.0
