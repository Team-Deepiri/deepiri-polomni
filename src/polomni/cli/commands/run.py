"""Integration orchestration commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from polomni.integration.benchmarks import run_benchmark_suite
from polomni.integration.workflow import run_lab_workflow
from polomni.observatory.reports.detection_report import format_report

app = typer.Typer(help="Run integrated lab workflows and benchmarks.")
console = Console()


@app.command("workflow")
def workflow_run(
    nside: Annotated[int, typer.Option("--nside", help="Target HEALPix NSIDE for RBLE scan.")] = 64,
    nulls: Annotated[int, typer.Option("--nulls", help="Null ensemble size.")] = 10,
    no_gw: Annotated[bool, typer.Option("--no-gw", help="Skip GWOSC refresh during ingest.")] = False,
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="JSON output path.")
    ] = None,
) -> None:
    """Ingest data, simulate district graph, and run the RBLE observatory pipeline."""
    result = run_lab_workflow(
        target_nside=nside,
        null_ensemble=nulls,
        fetch_gw=not no_gw,
    )

    sim = result.simulation_summary
    console.print(
        f"[green]Simulation[/green] {sim['packets_spawned']} packets, "
        f"{sim['graph_nodes']} nodes, {sim['graph_edges']} edges"
    )
    console.print(f"[green]GW catalog[/green] {result.gw_count} events")
    console.print(format_report(result.pipeline_result.detection))
    if result.pipeline_result.planck_lambda is not None:
        console.print(
            f"[dim]Planck Ω_Λ h² proxy: {result.pipeline_result.planck_lambda:.5f}[/dim]"
        )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {output}[/green]")


@app.command("benchmark")
def benchmark_run(
    nsides: Annotated[
        Optional[list[int]],
        typer.Option("--nside", help="NSIDE values to benchmark (repeatable)."),
    ] = None,
) -> None:
    """Profile RBLE signature computation across NSIDE resolutions."""
    rows = run_benchmark_suite(nsides)
    table = Table(title="RBLE Signature Benchmarks")
    table.add_column("NSIDE", justify="right")
    table.add_column("NPIX", justify="right")
    table.add_column("Seconds", justify="right")
    table.add_column("S_RBLE", justify="right")
    for row in rows:
        table.add_row(
            str(row["nside"]),
            str(row["npix"]),
            f"{row['seconds']:.4f}",
            f"{row['rble_score']:.4f}",
        )
    console.print(table)
