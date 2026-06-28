"""Polomni environment and cache info command."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import polomni

app = typer.Typer(help="Show Polomni version, dependencies, and cache status.", invoke_without_command=True)
console = Console()


def _optional_import(name: str) -> tuple[bool, str]:
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", "installed")
        return True, str(version)
    except ImportError:
        return False, "not installed"


@app.callback()
def info_cmd(
    ctx: typer.Context,
) -> None:
    """Print version, Python runtime, optional deps, and data cache summary."""
    if ctx.invoked_subcommand is not None:
        return

    from polomni.observatory.pipeline.cache import DataCache, default_cache_dir
    from polomni.observatory.pipeline.processor import list_cached_products
    from polomni.observatory.pipeline.sources.gwosc import load_cached_gwtc

    healpy_ok, healpy_ver = _optional_import("healpy")
    astropy_ok, astropy_ver = _optional_import("astropy")

    cache = DataCache()
    cached = list_cached_products(cache)
    present = [pid for pid, path in cached.items() if path is not None]

    gw_snapshot = load_cached_gwtc(cache)
    gw_count = gw_snapshot.results_count if gw_snapshot is not None else None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Version", polomni.__version__)
    table.add_row("Python", sys.version.split()[0])
    table.add_row(
        "healpy",
        healpy_ver if healpy_ok else "[red]not installed[/red]",
    )
    table.add_row(
        "astropy",
        astropy_ver if astropy_ok else "[red]not installed[/red]",
    )
    table.add_row("Cache dir", str(default_cache_dir()))
    table.add_row("Cached products", str(len(present)))
    if present:
        table.add_row("", ", ".join(sorted(present)))
    if gw_count is not None:
        table.add_row("GW events (cached)", str(gw_count))
    else:
        table.add_row("GW events (cached)", "[dim]none[/dim]")

    console.print(
        Panel(
            table,
            title="[bold]Polomni Info[/bold]",
            border_style="blue",
        )
    )
