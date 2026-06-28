"""CLI tests for polomni viz."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from polomni.cli.main import app

runner = CliRunner()


def test_viz_sky_synthetic(tmp_path: Path) -> None:
    out = tmp_path / "sky.png"
    result = runner.invoke(
        app,
        ["viz", "sky", "--synthetic", "--nside", "16", "--output", str(out)],
    )
    assert result.exit_code == 0, result.stdout
    assert out.is_file()
    assert out.stat().st_size > 0


def test_viz_district(tmp_path: Path) -> None:
    out = tmp_path / "district.png"
    result = runner.invoke(
        app,
        ["viz", "district", "--districts", "2", "--choices", "3", "--output", str(out)],
    )
    assert result.exit_code == 0, result.stdout
    assert out.is_file()
    assert out.stat().st_size > 0
