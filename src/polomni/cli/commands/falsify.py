"""Falsification trinity CLI — synthetic and real-data verification."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from polomni.math.falsification_runner import run_falsification

app = typer.Typer(help="Run RBLE falsification trinity (P1–P3) with optional real data.")
console = Console()


@app.callback(invoke_without_command=True)
def falsify_main(
    ctx: typer.Context,
    real: Annotated[bool, typer.Option("--real", help="Verify on cached WMAP/Planck/GW data.")] = False,
    fetch: Annotated[
        bool, typer.Option("--fetch", help="Fetch lite catalog before verification.")
    ] = False,
    nside: Annotated[int, typer.Option("--nside", help="HEALPix nside for map scoring.")] = 128,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON only.")] = False,
) -> None:
    """Run P1–P3 falsification checks and emit unified report."""
    if ctx.invoked_subcommand is not None:
        return

    report = run_falsification(real=real, fetch=fetch, target_nside=nside)
    if as_json:
        console.print(json.dumps(report.to_dict(), indent=2))
    else:
        table = Table(title=f"RBLE Falsification ({report.mode})")
        table.add_column("Scope")
        table.add_column("ID")
        table.add_column("Status")
        table.add_column("Residual")
        table.add_column("Message")
        for scope, rows in (("synthetic", report.synthetic), ("real", report.real)):
            for r in rows:
                status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
                table.add_row(scope, r.id, status, f"{r.residual:.4e}", r.message[:60])
        console.print(table)
        console.print(
            f"\n{report.passed_count}/{len(report.all_results)} passed "
            f"({'ALL OK' if report.all_passed else 'FAILURES'})"
        )
        if real and not report.data_ready:
            console.print("[yellow]Tip:[/yellow] polomni falsify --real --fetch")

    if not report.all_passed:
        raise typer.Exit(1)
