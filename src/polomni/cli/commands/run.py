"""Integration orchestration commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.benchmarks import run_benchmark_suite
from polomni.integration.closed_loop import run_closed_loop
from polomni.integration.loop_batch import run_loop_batch
from polomni.integration.loop_logger import log_loop_run
from polomni.integration.real_sky_bridge import run_physics_loop
from polomni.observatory.pipeline.cache import DataCache
from polomni.integration.workflow import run_lab_workflow
from polomni.observatory.reports.detection_report import format_report

app = typer.Typer(help="Run integrated lab workflows and benchmarks.")
console = Console()


@app.command("workflow")
def workflow_run(
    nside: Annotated[int, typer.Option("--nside", help="Target HEALPix NSIDE for RBLE scan.")] = 64,
    nulls: Annotated[int, typer.Option("--nulls", help="Null ensemble size.")] = 10,
    no_gw: Annotated[bool, typer.Option("--no-gw", help="Skip GWOSC refresh during ingest.")] = False,
    steps: Annotated[int, typer.Option("--steps", help="Closed-loop simulation steps.")] = 3,
    choices: Annotated[int, typer.Option("--choices", help="Branches per choice event.")] = 4,
    policy: Annotated[str, typer.Option("--policy", help="Choice policy: uniform|axis_biased|entropy_max.")] = "axis_biased",
    real_data: Annotated[bool, typer.Option("--real-data", help="Also run real-data RBLE pipeline.")] = False,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="JSON output path.")
    ] = None,
) -> None:
    """Closed RBLE loop: sim → CMB imprint → scan → feedback (+ subsystem suite)."""
    result = run_lab_workflow(
        target_nside=nside,
        null_ensemble=nulls,
        fetch_gw=not no_gw,
        simulation_choices=choices,
        closed_loop_steps=steps,
        policy=ChoicePolicy(policy),
        use_real_data_pipeline=real_data,
    )

    sim = result.simulation_summary
    console.print(
        f"[green]Closed loop[/green] {sim['closed_loop_steps']} steps, "
        f"policy={sim['policy']}, final axis error={sim['final_axis_error_deg']:.2f}°"
    )
    console.print(
        f"[green]Graph[/green] {sim['graph_nodes']} nodes, {sim['graph_edges']} edges, "
        f"mean S_RBLE={sim['mean_rble_score']:.4f}"
    )
    if result.pipeline_result is not None:
        console.print(f"[green]GW catalog[/green] {result.gw_count} events")
        console.print(format_report(result.pipeline_result.detection))
    if result.subsystems:
        inf = result.subsystems.get("inflation", {})
        console.print(
            f"[dim]Inflation D_eff mean={inf.get('mean_deff', 0):.2e}, "
            f"f_NL range={inf.get('fnl_range')}[/dim]"
        )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {output}[/green]")


@app.command("closed-loop")
def closed_loop_run(
    steps: Annotated[int, typer.Option("--steps")] = 3,
    choices: Annotated[int, typer.Option("--choices")] = 4,
    nside: Annotated[int, typer.Option("--nside")] = 64,
    policy: Annotated[str, typer.Option("--policy")] = "axis_biased",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Run only the closed simulation → imprint → scan → feedback loop."""
    graph, results = run_closed_loop(
        steps=steps,
        num_choices=choices,
        nside=nside,
        policy=ChoicePolicy(policy),
    )
    log_path = log_loop_run(
        graph,
        results,
        policy=ChoicePolicy(policy),
        nside=nside,
        seed=0,
    )
    table = Table(title="Closed Loop Steps")
    table.add_column("Step")
    table.add_column("Axis error (°)")
    table.add_column("S_RBLE")
    for r in results:
        table.add_row(str(r.step), f"{r.axis_error_deg:.2f}", f"{r.rble_score:.4f}")
    console.print(table)
    console.print(f"Graph: {graph.graph.number_of_nodes()} nodes")
    console.print(f"[dim]Logged {log_path}[/dim]")

    if output is not None:
        payload = {
            "steps": [r.to_dict() for r in results],
            "graph": graph.to_dict(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {output}[/green]")


@app.command("loop-batch")
def loop_batch_run(
    count: Annotated[int, typer.Option("--count", help="Number of loop runs.")] = 10,
    steps: Annotated[int, typer.Option("--steps")] = 3,
    choices: Annotated[int, typer.Option("--choices")] = 4,
    nside: Annotated[int, typer.Option("--nside")] = 32,
    policy: Annotated[str, typer.Option("--policy")] = "axis_biased",
    workers: Annotated[int, typer.Option("--workers", help="Parallel workers (1=sequential).")] = 1,
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Generate neural training corpus via batch closed-loop runs."""
    result = run_loop_batch(
        count=count,
        steps=steps,
        num_choices=choices,
        nside=nside,
        policy=ChoicePolicy(policy),
        workers=workers,
    )
    console.print(
        f"[green]Batch complete[/green] {result.n_runs} runs → {result.output_dir}, "
        f"mean final axis error={result.mean_final_error_deg:.2f}°"
    )
    console.print("[dim]Train with: polomni neural train[/dim]")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {output}[/green]")


@app.command("physics-loop")
def physics_loop_run(
    steps: Annotated[int, typer.Option("--steps")] = 3,
    nside: Annotated[int, typer.Option("--nside")] = 64,
    map_product: Annotated[
        str, typer.Option("--map-product", help="Cached CMB product id (e.g. wmap_k_band).")
    ] = "wmap_k_band",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Run closed loop biased toward real-sky preferred axis from cached map."""
    result = run_physics_loop(
        steps=steps,
        nside=nside,
        map_product_id=map_product,
        cache=DataCache(),
    )
    table = Table(title="Physics Loop (Real Sky Bridge)")
    table.add_column("Step")
    table.add_column("Separation (°)")
    table.add_column("Alignment")
    table.add_column("S_RBLE")
    for s in result.steps:
        table.add_row(
            str(s.step),
            f"{s.separation_deg:.2f}",
            f"{s.alignment_quality:.4f}",
            f"{s.rble_score:.4f}",
        )
    console.print(table)
    console.print(
        f"Real axis score={result.real_score:.4f}, "
        f"map={result.map_product_id}, nside={result.nside}"
    )

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        console.print(f"[green]Wrote {output}[/green]")


@app.command("benchmark")
def benchmark_run(
    nsides: Annotated[
        list[int] | None,
        typer.Option("--nside", help="NSIDE values to benchmark (repeatable)."),
    ] = None,
) -> None:
    """Profile RBLE signature computation across NSIDE resolutions."""
    rows = run_benchmark_suite(nsides)
    table = Table(title="RBLE Signature Benchmarks")
    table.add_column("NSIDE", justify="right")
    table.add_column("NPIX", justify="right")
    table.add_column("Seconds", justify="right")
    table.add_column("S_RBLE", justify="right")
    for row in rows:
        table.add_row(
            str(row["nside"]),
            str(row["npix"]),
            f"{row['seconds']:.4f}",
            f"{row['rble_score']:.4f}",
        )
    console.print(table)
