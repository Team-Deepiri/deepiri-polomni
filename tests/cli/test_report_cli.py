"""Tests for report CLI."""

from pathlib import Path

from typer.testing import CliRunner

from polomni.cli.main import app
from polomni.observatory.reports.detection_report import save_json
from polomni.observatory.scoring.rble_signature import compute_rble_signature
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map

runner = CliRunner()


def test_report_list_and_show(tmp_path: Path) -> None:
    cmb = synthetic_cmb_map(16, seed=0)
    det = compute_rble_signature(cmb)
    path = save_json(det, tmp_path / "r1.json")
    result = runner.invoke(app, ["report", "list", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "r1.json" in result.stdout
    show = runner.invoke(app, ["report", "show", str(path)])
    assert show.exit_code == 0
    assert "S_RBLE" in show.stdout
