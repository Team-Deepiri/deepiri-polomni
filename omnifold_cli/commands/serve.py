"""FastAPI health and status endpoint."""

from __future__ import annotations

import typer
import uvicorn
from fastapi import FastAPI

app = typer.Typer(help="Serve Omnifold lab API.")

api = FastAPI(title="Deepiri Omnifold Lab", version="0.1.0")


@api.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "omnifold-lab"}


@api.get("/")
def root() -> dict[str, str]:
    """Service metadata."""
    return {"name": "deepiri-omnifold", "framework": "RBLE"}


@app.callback(invoke_without_command=True)
def run(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8091, "--port"),
) -> None:
    """Start the Omnifold lab FastAPI server."""
    uvicorn.run(api, host=host, port=port, log_level="info")
