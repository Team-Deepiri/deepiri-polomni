"""Neural / heuristic CMB scar scoring wrapper."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from polomni.observatory.filters.radon_bifurcation import _radon_profile_s2
from polomni.observatory.scoring.rble_signature import compute_rble_signature


def _numpy_radon_variance_score(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
) -> float:
    """Fast numpy heuristic: variance of Radon profile along preferred axis."""
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    if n_hat is None:
        report = compute_rble_signature(healpix_map, scan_angles=12)
        axis = np.asarray(report.preferred_axis, dtype=float)
    else:
        axis = np.asarray(n_hat, dtype=float)
        axis = axis / (np.linalg.norm(axis) + 1e-15)

    profile = _radon_profile_s2(healpix_map, axis)
    map_rms = float(np.std(healpix_map)) + 1e-12
    return float(np.var(profile) / map_rms)


def _scar_model_score(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None,
    checkpoint_dir: Path | str | None,
) -> float | None:
    """Score with trained scar classifier when checkpoint exists."""
    from polomni.neural.scar_classifier.train_scar import load_scar_classifier
    from polomni.observatory.scoring.radon_tomography import build_radon_tomogram

    engine = load_scar_classifier(checkpoint_dir)
    if engine is None:
        return None

    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    if n_hat is None:
        report = compute_rble_signature(healpix_map, scan_angles=12)
        axis = np.asarray(report.preferred_axis, dtype=float)
    else:
        axis = np.asarray(n_hat, dtype=float)
        axis = axis / (np.linalg.norm(axis) + 1e-15)

    tomo = build_radon_tomogram(healpix_map, axis, n_eta=24, method="pixel")
    fingerprint = np.array(
        [tomo.score_integral, tomo.score_bifurcation, float(np.std(healpix_map))],
        dtype=float,
    )
    # Parent feature placeholder matching NODE_FEATURE_DIM=8 training pad.
    parent = np.zeros(8, dtype=float)
    parent[0] = 1.0
    parent[4:7] = axis
    parent[7] = 1.0
    x = np.concatenate([fingerprint, parent]).reshape(1, -1)
    # Engine may expect different feat dim — pad/truncate.
    need = engine.node_features
    if x.shape[1] < need:
        x = np.pad(x, ((0, 0), (0, need - x.shape[1])))
    elif x.shape[1] > need:
        x = x[:, :need]
    pred = engine.forward(x)[0]
    pred = pred / (np.linalg.norm(pred) + 1e-15)
    alignment = abs(float(np.dot(pred[:3], axis[:3])))
    return float(alignment * (1.0 + tomo.score_integral))


def score_map(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
    *,
    checkpoint_dir: Path | str | None = None,
) -> float:
    """Score a HEALPix map for RBLE scar signatures.

    Prefers a trained scar-classifier checkpoint; otherwise Radon-variance heuristic.
    """
    trained = _scar_model_score(healpix_map, n_hat, checkpoint_dir)
    if trained is not None:
        return trained
    return _numpy_radon_variance_score(healpix_map, n_hat=n_hat)


def predict_preferred_axis(
    healpix_map: np.ndarray,
    *,
    checkpoint_dir: Path | str | None = None,
) -> np.ndarray | None:
    """Neural axis guess from coarse tomogram fingerprint, or None if untrained."""
    from polomni.neural.scar_classifier.train_scar import load_scar_classifier
    from polomni.observatory.scoring.radon_tomography import build_radon_tomogram

    engine = load_scar_classifier(checkpoint_dir)
    if engine is None:
        return None
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    report = compute_rble_signature(healpix_map, scan_angles=8)
    axis = np.asarray(report.preferred_axis, dtype=float)
    tomo = build_radon_tomogram(healpix_map, axis, n_eta=16, method="pixel")
    fingerprint = np.array(
        [tomo.score_integral, tomo.score_bifurcation, float(np.std(healpix_map))],
        dtype=float,
    )
    parent = np.zeros(8, dtype=float)
    parent[0] = 1.0
    parent[4:7] = axis
    parent[7] = 1.0
    x = np.concatenate([fingerprint, parent]).reshape(1, -1)
    need = engine.node_features
    if x.shape[1] < need:
        x = np.pad(x, ((0, 0), (0, need - x.shape[1])))
    elif x.shape[1] > need:
        x = x[:, :need]
    pred = engine.forward(x)[0]
    pred = pred / (np.linalg.norm(pred) + 1e-15)
    return pred[:3]
