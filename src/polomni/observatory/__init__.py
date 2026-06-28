"""CMB observatory layer: HEALPix ingest, Radon-bifurcation filters, RBLE scar scoring."""

from polomni.observatory.scoring.rble_signature import DetectionReport, compute_rble_signature

__all__ = ["DetectionReport", "compute_rble_signature"]
