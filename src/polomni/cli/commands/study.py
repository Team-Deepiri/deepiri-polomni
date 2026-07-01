"""Pre-registered study CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from polomni.observatory.studies.gates import load_latest_result, run_p1_gates, run_p1_gates_full
from polomni.observatory.studies.p1_runner import run_p1_study

app = typer.Typer(help="Run pre-registered RBLE observatory studies.")
console = Console()


@app.command("gates")
def study_gates(
    config: Annotated[Path | None, typer.Option("--config", help="Study config JSON.")] = None,
    full: Annotated[bool, typer.Option("--full", help="Include Gate 4 if holdout exists.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON only.")] = False,
) -> None:
    """Check Gates 1–3 (or 1–4 with --full) before/after blind holdout."""
    report = run_p1_gates_full(config, require_blind=full)
    if as_json:
        console.print(json.dumps(report.to_dict(), indent=2))
    else:
        table = Table(title="P1 Physics Gates (pre-holdout)")
        table.add_column("Gate")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Message")
        for c in report.checks:
            status = "[green]PASS[/green]" if c.passed else "[red]FAIL[/red]"
            table.add_row(c.gate, c.name, status, c.message[:60])
        console.print(table)
        console.print(f"\n{report.passed_count}/{len(report.checks)} gates passed")
    if not report.all_passed:
        raise typer.Exit(1)


@app.command("status")
def study_status() -> None:
    """Show latest P1 RESULT.json summary if present."""
    result = load_latest_result()
    if result is None:
        console.print("[yellow]No RESULT.json yet[/yellow] — run: polomni study run p1 --calibration")
        raise typer.Exit(1)
    console.print(f"[bold]P1 study[/bold] mode={result.get('mode')} blind={result.get('blind')}")
    console.print(f"  map: {result.get('map_product_id')}  S={result['detection']['rble_score']:.4f}")
    console.print(f"  P1 supported: {result.get('p1_supported')}")
    console.print(f"  path: {result.get('result_path', 'data/studies/p1_holdout/RESULT.json')}")


@app.command("run")
def study_run(
    study: Annotated[str, typer.Argument(help="Study id (p1).")],
    config: Annotated[Path | None, typer.Option("--config", help="Study config JSON.")] = None,
    blind: Annotated[bool, typer.Option("--blind", help="Holdout map (Planck SMICA).")] = False,
    calibration: Annotated[
        bool, typer.Option("--calibration", help="Calibration map (WMAP) only.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON only.")] = False,
) -> None:
    """Run a frozen pre-registered study."""
    if study.lower() != "p1":
        console.print(f"[red]Unknown study:[/red] {study!r} (supported: p1)")
        raise typer.Exit(1)

    try:
        result = run_p1_study(config, blind=blind, calibration=calibration or (not blind))
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        console.print("[dim]Hint: polomni data fetch wmap_k_band --no-lite[/dim]")
        raise typer.Exit(1) from exc

    if as_json:
        console.print(json.dumps(result, indent=2))
    else:
        console.print(f"[green]Study complete[/green] mode={result['mode']}")
        console.print(f"  S_RBLE={result['detection']['rble_score']:.4f}")
        console.print(f"  P1 supported: {result['p1_supported']}")
        console.print(f"  Written: {result['result_path']}")

    if blind and not result["p1_supported"]:
        raise typer.Exit(2)
