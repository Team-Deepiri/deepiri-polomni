"""Frontend dev server helpers."""

from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path

import typer

app = typer.Typer(help="Multiverse React frontend (Vite).")
REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND = REPO_ROOT / "frontend"


@app.command("dev")
def frontend_dev(
    port: int = typer.Option(5173, "--port"),
    open_browser: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """Start Vite dev server (run `polomni serve` separately for API)."""
    if not (FRONTEND / "package.json").is_file():
        typer.echo("frontend/ not initialized. Run: cd frontend && npm install")
        raise typer.Exit(1)
    if open_browser:
        webbrowser.open(f"http://localhost:{port}")
    subprocess.run(["npm", "run", "dev", "--", "--port", str(port)], cwd=FRONTEND, check=True)


@app.command("build")
def frontend_build() -> None:
    """Build production frontend to frontend/dist/."""
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True)
    typer.echo(f"Built {FRONTEND / 'dist'}")
