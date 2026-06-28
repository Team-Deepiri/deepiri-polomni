"""FastAPI health and status endpoint."""

from __future__ import annotations

import typer
import uvicorn

from polomni.api import create_app

app = typer.Typer(help="Serve Polomni lab API.")

api = create_app()


@app.callback(invoke_without_command=True)
def run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8091, "--port"),
) -> None:
    """Start the Polomni lab FastAPI server."""
    uvicorn.run(api, host=host, port=port, log_level="info")


def main() -> None:
    """Console script entry for polomni-serve."""
    app()
