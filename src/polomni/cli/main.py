"""Typer CLI entrypoint for the Deepiri Polomni Engine."""

from __future__ import annotations

import typer

from polomni.cli.commands import falsify, frontend, info, math, neural, report, run, scan, serve, simulate, study, viz
from polomni.observatory.pipeline import cli_commands as data

app = typer.Typer(
    name="polomni",
    help="Deepiri Polomni Engine — RBLE simulation and CMB observatory CLI.",
    no_args_is_help=True,
)

app.add_typer(simulate.app, name="simulate")
app.add_typer(scan.app, name="scan")
app.add_typer(serve.app, name="serve")
app.add_typer(data.app, name="data")
app.add_typer(run.app, name="run")
app.add_typer(viz.app, name="viz")
app.add_typer(info.app, name="info")
app.add_typer(report.app, name="report")
app.add_typer(math.app, name="math")
app.add_typer(falsify.app, name="falsify")
app.add_typer(study.app, name="study")
app.add_typer(neural.app, name="neural")
app.add_typer(frontend.app, name="frontend")


def main() -> None:
    """Console script entry."""
    app()


if __name__ == "__main__":
    main()
