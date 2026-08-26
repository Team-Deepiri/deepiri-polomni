"""Analytic bubble-collision template for RDF/RQF projection (Cai et al. 2025 class).

A bubble collision about axis n̂_c imprints azimuthally symmetric superhorizon
modes: a dipole (RDF class) and quadrupole (RQF class) sharing the same symmetry
axis. This module defines the **combined template score** used in P5 Phase B.

Reference: Cai, Zhang, Guan — arXiv:2510.12134 (bubble template on RQF).
Polomni uses a simplified closed-form proxy (no RemoteField dependency).
"""

from __future__ import annotations

import numpy as np

# Relative RDF:RQF amplitude ratio from axisymmetric bubble collision (forecast class).
DEFAULT_RDF_WEIGHT = 1.0
DEFAULT_RQF_WEIGHT = 0.65


def bubble_template_score(
    rdf_score: float,
    rqf_score: float,
    *,
    w_rdf: float = DEFAULT_RDF_WEIGHT,
    w_rqf: float = DEFAULT_RQF_WEIGHT,
) -> float:
    """Coherent bubble template: dipole + quadrupole with matching sign.

    The product term rewards axes where both multipoles are significant and
    **same-signed** (coherent collision imprint). The weighted sum adds linear
    sensitivity for weak signals.
    """
    rdf = float(rdf_score)
    rqf = float(rqf_score)
    sign_coherent = 1.0 if rdf * rqf >= 0 else -0.25
    linear = w_rdf * abs(rdf) + w_rqf * abs(rqf)
    product = abs(rdf * rqf)
    return sign_coherent * (linear + product)


def bubble_template_scores_batch(
    rdf_scores: np.ndarray,
    rqf_scores: np.ndarray,
    *,
    w_rdf: float = DEFAULT_RDF_WEIGHT,
    w_rqf: float = DEFAULT_RQF_WEIGHT,
) -> np.ndarray:
    """Vectorized bubble_template_score."""
    rdf = np.asarray(rdf_scores, dtype=float)
    rqf = np.asarray(rqf_scores, dtype=float)
    sign = np.where(rdf * rqf >= 0, 1.0, -0.25)
    linear = w_rdf * np.abs(rdf) + w_rqf * np.abs(rqf)
    product = np.abs(rdf * rqf)
    return sign * (linear + product)
