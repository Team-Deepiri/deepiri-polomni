"""Tests for IRAS PSCz fetch/parse."""

from __future__ import annotations

from polomni.observatory.pipeline.sources.iras_pscz import parse_pscz_tsv


def test_parse_pscz_tsv_skips_headers() -> None:
    text = """# comment
_RA.icrs\t_DE.icrs\tS60\tHvel
deg\tdeg\tJy\tkm/s
----------\t--------\t----\t----
10.5\t-20.1\t1.2\t3000
bad\trow\tx\ty
45.0\t10.0\t0.8\t1500
"""
    rows = parse_pscz_tsv(text)
    assert len(rows) == 2
    assert rows[0]["ra"] == 10.5
    assert rows[1]["dec"] == 10.0
