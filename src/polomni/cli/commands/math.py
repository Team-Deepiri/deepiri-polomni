"""Math proof CLI commands."""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from polomni.math.proofs.base import prove_all

app = typer.Typer(help="Run RBLE mathematical proof suite.")
console = Console()


@app.command("prove")
def math_prove(
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON only.")] = False,
    strict: Annotated[
        bool, typer.Option("--strict", help="SymPy + convergence proofs with baselines.")
    ] = False,
    real_data: Annotated[
        bool, typer.Option("--real-data", help="Verify against cached Planck/WMAP/GW.")
    ] = False,
) -> None:
    """Run all equation and falsification proofs."""
    suite = prove_all(strict=strict, real_data=real_data)
    if as_json:
        console.print(json.dumps(suite.to_dict(), indent=2))
    else:
        table = Table(title="RBLE Math Proof Suite")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Residual")
        table.add_column("Message")
        for r in suite.results:
            status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            table.add_row(r.id, r.name or r.id, status, f"{r.residual:.4e}", r.message[:50])
        console.print(table)
        console.print(
            f"\n{suite.passed_count}/{len(suite.results)} passed "
            f"({'ALL OK' if suite.all_passed else 'FAILURES'})"
        )
    if not suite.all_passed:
        raise typer.Exit(1)


@app.command("equations")
def math_equations() -> None:
    """List the eight master equations and variational principle."""
    from polomni.math.catalog import EQUATION_CATALOG

    table = Table(title="RBLE Equation Catalog")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Module")
    for eq in EQUATION_CATALOG:
        table.add_row(eq["id"], eq["name"], eq["module"])
    console.print(table)
