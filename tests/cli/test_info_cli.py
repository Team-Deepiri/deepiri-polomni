"""CLI tests for polomni info."""

from __future__ import annotations

from typer.testing import CliRunner

from polomni.cli.main import app

runner = CliRunner()


def test_info_runs() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Polomni Info" in result.stdout
    assert "0.1.0" in result.stdout
