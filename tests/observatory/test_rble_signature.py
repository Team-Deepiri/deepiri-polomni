"""Observatory tests for RBLE scar signature detection."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.reports.detection_report import format_report, save_json
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import (
    compute_rble_signature,
    inject_synthetic_scar,
)


@pytest.mark.observatory
def test_synthetic_scar_detection_above_null() -> None:
    """Injected Radon scar should score above isotropic null ensemble."""
    nside = 32
    seed = 7
    n_hat = np.array([0.2, 0.3, 0.93])
    n_hat /= np.linalg.norm(n_hat)

    base = synthetic_cmb_map(nside, seed=seed)
    scarred = inject_synthetic_scar(base, n_hat, amplitude=8.0)

    detection = compute_rble_signature(scarred, n_hat=n_hat)
    null_maps = generate_null_ensemble(30, nside, seed=seed + 100)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]

    null_mu = float(np.mean(null_scores))
    null_sigma = float(np.std(null_scores)) + 1e-12
    significance = (detection.rble_score - null_mu) / null_sigma

    assert detection.rble_score > null_mu
    assert significance > 1.0
    assert detection.falsification_flags["radon_anisotropic"] is True

    text = format_report(detection)
    assert "RBLE Detection Report" in text
    assert "S_RBLE" in text


@pytest.mark.observatory
def test_detection_report_json_roundtrip(tmp_path) -> None:
    """save_json writes valid DetectionReport payload."""
    nside = 16
    n_hat = [0.0, 0.0, 1.0]
    scarred = inject_synthetic_scar(synthetic_cmb_map(nside, seed=1), n_hat, amplitude=5.0)
    report = compute_rble_signature(scarred, n_hat=n_hat)

    out = save_json(report, tmp_path / "report.json")
    assert out.exists()
    assert "rble_score" in out.read_text(encoding="utf-8")
