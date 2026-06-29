"""Real-data fetch, pipeline, and watch commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from polomni.observatory.pipeline.cache import DataCache, default_cache_dir
from polomni.observatory.pipeline.catalog import CATALOG, LITE_PRODUCT_IDS, STANDARD_FETCH_IDS, get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.processor import list_cached_products, run_rble_pipeline
from polomni.observatory.pipeline.scheduler import WatchEvent, watch_realtime
from polomni.observatory.reports.detection_report import format_report

app = typer.Typer(help="Fetch and run real cosmology data pipeline.")
console = Console()


@app.command("list")
def list_data() -> None:
    """List available online data products."""
    table = Table(title="Polomni Data Catalog")
    table.add_column("ID")
    table.add_column("Tier")
    table.add_column("Mission")
    table.add_column("Description")
    for p in CATALOG.values():
        table.add_row(p.id, p.tier, p.mission, p.description[:60] + "…")
    console.print(table)


@app.command("status")
def status() -> None:
    """Show cached data files."""
    cache = DataCache()
    console.print(f"[dim]Cache: {default_cache_dir()}[/dim]")
    paths = list_cached_products(cache)
    for pid, path in paths.items():
        if path:
            mb = path.stat().st_size / (1024 * 1024)
            console.print(f"  [green]✓[/green] {pid}: {path} ({mb:.1f} MB)")
        else:
            console.print(f"  [dim]○[/dim] {pid}: not cached")


@app.command("fetch")
def fetch(
    products: Annotated[
        list[str] | None,
        typer.Argument(help="Product IDs (default: lite set)."),
    ] = None,
    lite: Annotated[bool, typer.Option("--lite", help="Fetch lite products when no IDs given.")] = True,
    no_lite: Annotated[
        bool, typer.Option("--no-lite", help="Skip default lite product set.")
    ] = False,
    wmap: Annotated[bool, typer.Option("--wmap", help="Also fetch WMAP K-band map (~100 MB).")] = False,
    planck: Annotated[
        bool, typer.Option("--planck", help="Also fetch Planck SMICA map (~384 MB).")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Re-download even if cache is fresh.")] = False,
    gw: Annotated[bool, typer.Option("--gw", help="Refresh GWOSC GWTC catalog.")] = True,
    no_gw: Annotated[bool, typer.Option("--no-gw", help="Skip GWOSC catalog refresh.")] = False,
) -> None:
    """Download real data from NASA/IRSA/GWOSC into local cache."""
    cache = DataCache()
    ids = list(products) if products else []
    if not ids and lite and not no_lite:
        ids.extend(LITE_PRODUCT_IDS)
    if wmap:
        ids.append("wmap_k_band")
    if planck:
        ids.append("planck_smica_cmb")
    if not ids:
        ids = list(STANDARD_FETCH_IDS)

    for pid in dict.fromkeys(ids):
        product = get_product(pid)
        console.print(f"[cyan]Fetching[/cyan] {product.name}…")
        result = fetch_product(product, cache, force=force)
        src = "cache" if result.from_cache and not result.downloaded else "network"
        console.print(f"  → {result.path} ({result.bytes_written / 1024:.1f} KiB, {src})")

    if gw and not no_gw:
        from polomni.observatory.pipeline.sources.gwosc import fetch_gwtc_events

        snap = fetch_gwtc_events(cache)
        console.print(f"[green]GWTC[/green] {snap.results_count} events cached")


@app.command("pipeline")
def pipeline_run(
    map_product: Annotated[
        str | None,
        typer.Option("--map-product", help="CMB map product ID (default: wmap_k_band)."),
    ] = None,
    planck: Annotated[
        bool, typer.Option("--planck", help="Use Planck SMICA map instead of WMAP.")
    ] = False,
    nside: Annotated[int, typer.Option("--nside", help="Target HEALPix NSIDE for RBLE scan.")] = 128,
    nulls: Annotated[int, typer.Option("--nulls", help="Null ensemble size.")] = 30,
    force: Annotated[bool, typer.Option("--force", help="Re-fetch data before scan.")] = False,
    no_gw: Annotated[bool, typer.Option("--no-gw", help="Skip GWOSC refresh during ingest.")] = False,
    report_dir: Annotated[
        Path, typer.Option("--report-dir", help="Directory for JSON detection reports.")
    ] = Path("data/reports"),
) -> None:
    """Fetch real data and run full RBLE observatory pipeline."""
    pid = map_product or ("planck_smica_cmb" if planck else "wmap_k_band")
    result = run_rble_pipeline(
        map_product_id=pid,
        include_heavy=planck or pid == "planck_smica_cmb",
        force_fetch=force,
        target_nside=nside,
        null_ensemble=nulls,
        report_dir=report_dir,
        fetch_gw=not no_gw,
    )
    console.print(format_report(result.detection))
    if result.planck_lambda is not None:
        console.print(f"[dim]Planck Ω_Λ h² proxy: {result.planck_lambda:.5f}[/dim]")
    if result.ingest.gw_new_events:
        console.print(f"[yellow]{len(result.ingest.gw_new_events)} new GW events[/yellow]")
    if result.report_path:
        console.print(f"[green]Report: {result.report_path}[/green]")


@app.command("watch")
def watch(
    interval: Annotated[
        float, typer.Option("--interval", help="Poll interval in seconds.")
    ] = 300.0,
    iterations: Annotated[
        int | None, typer.Option("--iterations", help="Max poll cycles (default: unlimited).")
    ] = None,
    nside: Annotated[int, typer.Option("--nside", help="NSIDE for RBLE scans.")] = 128,
    scan_on_gw: Annotated[
        bool, typer.Option("--scan-on-gw", help="Re-run RBLE scan when new GW events appear.")
    ] = False,
) -> None:
    """Poll GWOSC and optionally re-run RBLE scans (real-time ingestion loop)."""

    def _on_event(evt: WatchEvent) -> None:
        color = "cyan" if evt.kind == "gw_poll" else "green"
        console.print(f"[{color}]{evt.timestamp.isoformat()}[/] {evt.message}")

    for _ in watch_realtime(
        interval_seconds=interval,
        max_iterations=iterations,
        on_event=_on_event,
        run_scan_on_gw_update=scan_on_gw,
        target_nside=nside,
    ):
        pass


plot_app = typer.Typer(help="Plot cached cosmology data.")
app.add_typer(plot_app, name="plot")


@plot_app.command("power")
def plot_power(
    product: Annotated[str, typer.Option("--product", help="Power spectrum product ID.")] = (
        "planck_cmb_tt_power"
    ),
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Plot cached CMB power spectrum."""
    from polomni.observatory.pipeline.analytics import plot_cached_power_spectrum

    path = plot_cached_power_spectrum(product_id=product, output_path=output)
    console.print(f"[green]Saved {path}[/green]")


@plot_app.command("gw")
def plot_gw(
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Max events to plot.")] = 50,
) -> None:
    """Plot GW event timeline from cached GWTC catalog."""
    from polomni.observatory.pipeline.analytics import plot_cached_gw_timeline

    path = plot_cached_gw_timeline(output_path=output, limit=limit)
    console.print(f"[green]Saved {path}[/green]")


@app.command("correlate")
def correlate(
    report: Annotated[Path | None, typer.Option("--report", "-r", help="Report JSON.")] = None,
    max_deg: Annotated[float, typer.Option("--max-deg", help="Max axis separation.")] = 30.0,
) -> None:
    """Correlate GW events with RBLE preferred axis from a report."""
    from polomni.observatory.pipeline.analytics import summarize_gw_rble_correlation

    matches = summarize_gw_rble_correlation(report_path=report, max_separation_deg=max_deg)
    if not matches:
        console.print("[yellow]No correlated GW events found (or no report/cache).[/yellow]")
        return
    table = Table(title=f"GW–RBLE Correlations (≤{max_deg}°)")
    table.add_column("Event")
    table.add_column("Separation (°)")
    for m in matches:
        table.add_row(str(m.get("name", m.get("event", "?"))), f"{m.get('separation_deg', 0):.1f}")
    console.print(table)
