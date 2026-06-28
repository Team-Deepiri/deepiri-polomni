"""Neural / heuristic CMB scar scoring wrapper."""

from __future__ import annotations

import numpy as np

from omnifold_observatory.scoring.rble_signature import compute_rble_signature


def score_map(
    healpix_map: np.ndarray,
    n_hat: np.ndarray | list[float] | None = None,
) -> float:
    """Score a HEALPix map for RBLE scar signatures.

    Delegates to :func:`compute_rble_signature` and returns the scalar
    ``rble_score``. A trained CNN may replace this when the ``torch`` group
    is installed and weights are available.

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
    report = compute_rble_signature(healpix_map, n_hat=n_hat)
    return report.rble_score
