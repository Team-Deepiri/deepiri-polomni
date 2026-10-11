"""Smoke test for Phase L DESI × amplitude locksmith wiring."""

from __future__ import annotations

from polomni.observatory.pipeline.sources.desi_amplitude_locksmith import (
    desi_amplitude_locksmith_report,
)


def test_desi_amplitude_module_importable() -> None:
    assert callable(desi_amplitude_locksmith_report)
