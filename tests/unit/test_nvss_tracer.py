"""Tests for NVSS parse + hammer helpers (no network for unit parse)."""

from __future__ import annotations

from polomni.observatory.pipeline.sources.nvss_tracer import parse_nvss_tsv


def test_parse_nvss_tsv_basic() -> None:
    sample = """# comment
_RAJ2000\t_DEJ2000\tS1.4
deg\tdeg\tmJy
---\t---\t---
10.5\t-20.1\t250.0
180.0\t45.0\t300.5
bad\trow\there
"""
    rows = parse_nvss_tsv(sample)
    assert len(rows) == 2
    assert rows[0]["ra"] == 10.5
    assert rows[1]["s14"] == 300.5
