"""Visualization CLI commands."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from rich.console import Console

app = typer.Typer(help="Generate Polomni visualization figures.")
console = Console()


def _default_figure_path(prefix: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("data/figures") / f"{prefix}_{ts}.png"


def _parse_highlight_axis(value: str | None) -> np.ndarray | None:
    if value is None:
        return None
    parts = [float(x.strip()) for x in value.split(",")]
    if len(parts) != 3:
        raise typer.BadParameter("highlight-axis must be three comma-separated floats: x,y,z")
    return np.array(parts, dtype=float)


@app.command("sky")
def viz_sky(
    real: Annotated[
        bool,
        typer.Option("--real/--synthetic", help="Load cached real CMB map or generate synthetic."),
    ] = False,
    map_product: Annotated[
        str,
        typer.Option("--map-product", help="Data product ID when --real is set."),
    ] = "wmap_k_band",
    nside: Annotated[
        int,
        typer.Option("--nside", help="NSIDE for synthetic or downsampled real map."),
    ] = 64,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="PNG output path."),
    ] = None,
    highlight_axis: Annotated[
        str | None,
        typer.Option("--highlight-axis", help="Optional axis vector as x,y,z."),
    ] = None,
) -> None:
    """Render a HEALPix CMB map in Mollweide projection."""
    from polomni.observatory.ingest.healpix_loader import (
        downsample_map,
        load_healpix_map,
        synthetic_cmb_map,
    )
    from polomni.viz.sky_map import plot_mollweide

    if real:
        from polomni.observatory.pipeline.cache import DataCache
        from polomni.observatory.pipeline.catalog import get_product
        from polomni.observatory.pipeline.downloader import fetch_product

        cache = DataCache()
        product = get_product(map_product)
        fetched = fetch_product(product, cache)
        raw = load_healpix_map(fetched.path, field="T")
        cmb_map = downsample_map(raw, nside)
        title = f"CMB ({map_product}, NSIDE={nside})"
        console.print(f"[dim]Real data: {map_product} → NSIDE={nside}[/dim]")
    else:
        cmb_map = synthetic_cmb_map(nside, seed=42)
        title = f"Synthetic CMB (NSIDE={nside})"
        console.print(f"[dim]Synthetic CMB map NSIDE={nside}[/dim]")

    out_path = output or _default_figure_path("sky")
    axis = _parse_highlight_axis(highlight_axis)
    plot_mollweide(
        cmb_map,
        title=title,
        save_path=out_path,
        highlight_axis=axis,
    )
    console.print(f"[green]Saved sky map to {out_path}[/green]")


@app.command("district")
def viz_district(
    districts: Annotated[
        int,
        typer.Option("--districts", "-d", help="Initial district count."),
    ] = 1,
    choices: Annotated[
        int,
        typer.Option("--choices", "-c", help="Choices per branching event."),
    ] = 5,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="PNG output path."),
    ] = None,
) -> None:
    """Simulate a short district branching run and plot the resulting DAG."""
    from polomni.core.superspace.district_graph import DistrictGraph
    from polomni.viz.district_graph_viz import plot_district_graph

    graph = DistrictGraph()
    root_ids: list[int] = []
    for i in range(districts):
        root_ids.append(
            graph.add_district(
                mass=1.0 + 0.1 * i,
                law_of_gravity=[6.674e-11, 1.1e-52],
                coordinate=[float(i), 0.0, 0.0],
                lambda_vacuum=1.0e-52,
            )
        )

    for root in root_ids:
        graph.trigger_choice_event(root, num_choices=choices)

    out_path = output or _default_figure_path("district")
    plot_district_graph(
        graph,
        title=f"District Graph ({districts} root(s), {choices} choices)",
        save_path=out_path,
    )
    console.print(
        f"[green]Saved district graph ({graph.graph.number_of_nodes()} nodes) to {out_path}[/green]"
    )


@app.command("stream")
def viz_stream(
    packets: Annotated[
        int,
        typer.Option("--packets", "-n", help="Number of Radon vacuum stream packets."),
    ] = 5,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="PNG output path."),
    ] = None,
) -> None:
    """Run Radon vacuum stream pipelines and plot per-packet flux."""
    from polomni.core.radon.vacuum_stream import RadonVacuumPipeline
    from polomni.viz.stream_pipeline_viz import plot_stream_pipeline

    stages: list[dict[str, float | str]] = []
    nx = 9
    coords = np.linspace(-1.5, 1.5, nx)

    for i in range(packets):
        xg, yg, zg = np.meshgrid(coords, coords, coords, indexing="ij")
        offset = 0.15 * i
        psi_field = np.exp(-((xg - offset) ** 2 + yg**2 + zg**2))

        pipeline = RadonVacuumPipeline(
            district_id=i,
            num_choices=3,
            horizon_area=4.0 * np.pi,
            rotation_angles=(0.1 * i, 0.2, 0.0),
            entropy_gradient=np.linspace(0.1, 0.4, 4),
        )
        bubble = pipeline.encapsulate_and_scan(psi_field)
        rotated = pipeline.rotate_particle_properties(bubble)
        packet = pipeline.stream_to_vacuum(rotated)

        stages.append({"name": f"scan_{i}", "flux": float(np.mean(np.abs(bubble)))})
        stages.append({"name": f"rotate_{i}", "flux": float(np.mean(np.abs(rotated)))})
        stages.append(
            {"name": f"stream_{i}", "flux": float(np.mean(packet.phi_stream))},
        )

    out_path = output or _default_figure_path("stream")
    plot_stream_pipeline(
        stages,
        title=f"Radon Vacuum Stream ({packets} packet(s))",
        save_path=out_path,
    )
    console.print(f"[green]Saved stream pipeline viz ({packets} packets) to {out_path}[/green]")
