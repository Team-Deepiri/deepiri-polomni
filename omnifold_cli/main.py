"""Typer CLI entrypoint for the Deepiri Omnifold Engine."""

from __future__ import annotations

import typer

from omnifold_cli.commands import scan, serve, simulate

app = typer.Typer(
    name="omnifold",
    help="Deepiri Omnifold Engine — RBLE simulation and CMB observatory CLI.",
    no_args_is_help=True,
)

app.add_typer(simulate.app, name="simulate")
app.add_typer(scan.app, name="scan")
app.add_typer(serve.app, name="serve")


def main() -> None:
    """Console script entry."""
    app()


if __name__ == "__main__":
    main()
