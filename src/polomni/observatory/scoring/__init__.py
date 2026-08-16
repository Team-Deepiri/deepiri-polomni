"""RBLE signature scoring and null hypothesis ensembles."""

from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.radon_tomography import build_radon_tomogram, rble_score_at_axis
from polomni.observatory.scoring.rble_signature import DetectionReport, compute_rble_signature
from polomni.observatory.scoring.snr import (
    attach_null_significance,
    empirical_p_value,
    null_moments,
    snr_from_null,
)

__all__ = [
    "DetectionReport",
    "attach_null_significance",
    "compute_rble_signature",
    "empirical_p_value",
    "generate_null_ensemble",
    "build_radon_tomogram",
    "null_moments",
    "rble_score_at_axis",
    "snr_from_null",
]
