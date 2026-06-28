"""Neural / heuristic CMB scar scoring wrapper."""

from __future__ import annotations

import numpy as np

from polomni.observatory.filters.radon_bifurcation import _radon_profile_s2
from polomni.observatory.scoring.rble_signature import compute_rble_signature


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _score_map_torch(healpix_map: np.ndarray, n_hat: np.ndarray | None) -> float | None:
    """Return CNN score when torch and trained weights are available."""
    if not _torch_available():
        return None
    # No bundled weights yet — fall through to numpy heuristic.
    return None


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


def score_map(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
) -> float:
    """Score a HEALPix map for RBLE scar signatures.

    Uses a trained CNN when ``torch`` and model weights are available;
    otherwise a numpy Radon-variance heuristic along the preferred axis.

    Parameters
    ----------
    healpix_map:
        Input map.
    n_hat:
        Optional fixed view axis.

    Returns
    -------
    float
        RBLE signature strength.
    """
    torch_score = _score_map_torch(healpix_map, n_hat)
    if torch_score is not None:
        return torch_score
    return _numpy_radon_variance_score(healpix_map, n_hat=n_hat)
