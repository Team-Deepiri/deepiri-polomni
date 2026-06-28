"""P1 injection recovery calibration tests (Gate 2)."""

import numpy as np
import pytest

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.rble_signature import compute_rble_signature, inject_synthetic_scar


def _axis_error_deg(true_axis: np.ndarray, recovered: list[float]) -> float:
    a = np.asarray(recovered, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-15)
    t = true_axis / (np.linalg.norm(true_axis) + 1e-15)
    dot = float(np.clip(np.dot(a, t), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


@pytest.mark.slow
def test_p1_injection_recovery_at_snr_3() -> None:
    """≥90% axis recovery within 5° at SNR≥3 (FALSIFICATION_CRITERIA)."""
    nside = 32
    amplitudes = {1: 3.0, 2: 6.0, 3: 12.0, 5: 18.0}
    snr_target = 3
    amplitude = amplitudes[snr_target]
    trials = 20
    successes = 0

    for trial in range(trials):
        axis = np.random.randn(3)
        axis /= np.linalg.norm(axis)
        cmb = synthetic_cmb_map(nside, seed=trial + 100)
        scarred = inject_synthetic_scar(cmb, axis, amplitude=amplitude)
        report = hierarchical_sky_search(scarred, coarse_nside=16, refine_samples=12, seed=trial)
        err = _axis_error_deg(axis, report.preferred_axis)
        if err < 5.0:
            successes += 1

    rate = successes / trials
    assert rate >= 0.9, f"recovery rate {rate:.2f} < 0.90 at SNR={snr_target}"


def test_injection_increases_score() -> None:
    nside = 16
    axis = np.array([0.0, 0.0, 1.0])
    cmb = synthetic_cmb_map(nside, seed=0)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=10.0)
    iso = compute_rble_signature(cmb, scan_angles=8)
    scar = compute_rble_signature(scarred, axis, scan_angles=1)
    assert scar.rble_score > iso.rble_score
