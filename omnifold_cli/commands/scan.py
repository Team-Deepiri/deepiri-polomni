"""CMB scar scan command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from omnifold_observatory.ingest.healpix_loader import load_healpix_map, synthetic_cmb_map
from omnifold_observatory.reports.detection_report import format_report, save_json
from omnifold_observatory.scoring.null_ensemble import generate_null_ensemble
from omnifold_observatory.scoring.rble_signature import compute_rble_signature

app = typer.Typer(help="Run CMB RBLE scar scan.")
console = Console()


@app.callback(invoke_without_command=True)
def run(
    map_path: Path | None = typer.Option(
        None, "--map", "-m", help="HEALPix FITS or .npy path (default: synthetic)."
    ),
    nside: int = typer.Option(64, "--nside", help="NSIDE for synthetic map."),
    seed: int = typer.Option(42, "--seed", help="RNG seed."),
    nulls: int = typer.Option(20, "--nulls", help="Null ensemble size for significance."),
    report: Path | None = typer.Option(None, "--report", "-r", help="JSON report output."),
) -> None:
    """Scan a CMB map for RBLE scar signatures."""
    if map_path is not None:
        cmb = load_healpix_map(map_path, field="T")
    else:
        cmb = synthetic_cmb_map(nside, seed=seed)
        console.print(f"[dim]Using synthetic CMB map NSIDE={nside}, seed={seed}[/dim]")

    detection = compute_rble_signature(cmb)

    null_maps = generate_null_ensemble(nulls, nside if map_path is None else 64, seed=seed + 1)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]
    mu = float(sum(null_scores) / len(null_scores))
    sigma = float((sum((s - mu) ** 2 for s in null_scores) / len(null_scores)) ** 0.5)
    if sigma > 0:
        detection.null_sigma = (detection.rble_score - mu) / sigma

    console.print(format_report(detection))

    if report is not None:
        path = save_json(detection, report)
        console.print(f"[green]Report saved to {path}[/green]")
