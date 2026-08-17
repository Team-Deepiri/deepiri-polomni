"""CLI tests for sealed P1 result handling."""

from typer.testing import CliRunner

from polomni.cli.main import app
from polomni.observatory.studies.results import publish_result

runner = CliRunner()


def test_blind_run_reports_sealed_result_conflict(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    publish_result(
        {"mode": "holdout_blind", "blind": True},
        mode="holdout_blind",
    )

    result = runner.invoke(app, ["study", "run", "p1", "--blind"])

    assert result.exit_code == 1
    assert "sealed" in result.stdout
    assert "--output" in result.stdout


def test_blind_rerun_accepts_explicit_alternate_output(
    monkeypatch,
    tmp_path,
) -> None:
    from polomni.cli.commands import study as study_command

    captured: dict = {}
    alternate = tmp_path / "replication" / "rerun.json"

    def fake_run_p1_study(config, **kwargs):
        captured.update(kwargs)
        return {
            "mode": "holdout_blind",
            "detection": {"rble_score": 1.0},
            "p1_supported": True,
            "result_path": str(kwargs["output_path"]),
        }

    monkeypatch.setattr(study_command, "run_p1_study", fake_run_p1_study)

    result = runner.invoke(
        app,
        ["study", "run", "p1", "--blind", "--output", str(alternate)],
    )

    assert result.exit_code == 0
    assert captured["output_path"] == alternate
