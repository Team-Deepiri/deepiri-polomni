"""CLI tests for polomni falsify."""

from typer.testing import CliRunner

from polomni.cli.main import app


def test_falsify_synthetic_passes() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["falsify"])
    assert result.exit_code == 0, result.stdout
