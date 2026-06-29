"""Detection report management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from polomni.observatory.reports.comparison import (
    compare_reports,
    format_comparison,
    latest_report,
    list_reports,
    load_report,
)
from polomni.observatory.reports.detection_report import format_report

app = typer.Typer(help="List, show, and compare RBLE detection reports.")
console = Console()


@app.command("list")
def report_list(
    directory: Annotated[Path, typer.Option("--dir", help="Reports directory.")] = Path("data/reports"),
) -> None:
    """List saved detection reports."""
    reports = list_reports(directory)
    if not reports:
        console.print(f"[dim]No reports in {directory}[/dim]")
        return
    table = Table(title="RBLE Detection Reports")
    table.add_column("File")
    table.add_column("Modified")
    for path in reports:
        mtime = path.stat().st_mtime
        table.add_row(path.name, f"{mtime:.0f}")
    console.print(table)


@app.command("show")
def report_show(
    path: Annotated[Path, typer.Argument(help="Report JSON path.")],
) -> None:
    """Display a detection report."""
    report = load_report(path)
    console.print(format_report(report))


@app.command("latest")
def report_latest(
    directory: Annotated[Path, typer.Option("--dir", help="Reports directory.")] = Path("data/reports"),
) -> None:
    """Show the most recent detection report."""
    path = latest_report(directory)
    if path is None:
        console.print(f"[yellow]No reports found in {directory}[/yellow]")
        raise typer.Exit(1)
    console.print(f"[dim]{path}[/dim]")
    console.print(format_report(load_report(path)))


@app.command("compare")
def report_compare(
    path_a: Annotated[Path, typer.Argument(help="First report JSON.")],
    path_b: Annotated[Path | None, typer.Argument(help="Second report (default: latest).")] = None,
    directory: Annotated[Path, typer.Option("--dir", help="Reports dir when path_b omitted.")] = Path(
        "data/reports"
    ),
) -> None:
    """Compare two detection reports."""
    if path_b is None:
        reports = list_reports(directory)
        if len(reports) < 2:
            console.print("[red]Need at least two reports to compare.[/red]")
            raise typer.Exit(1)
        path_b = reports[0] if reports[0] != path_a else reports[1]
    cmp = compare_reports(load_report(path_a), load_report(path_b))
    console.print(f"[dim]A: {path_a}[/dim]")
    console.print(f"[dim]B: {path_b}[/dim]")
    console.print(format_comparison(cmp))
