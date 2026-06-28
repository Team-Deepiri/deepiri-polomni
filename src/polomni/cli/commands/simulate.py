"""District DAG simulation command."""

from __future__ import annotations

import json
from pathlib import Path

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Run district multiverse simulation.")
console = Console()


@app.callback(invoke_without_command=True)
def run(
    choices: int = typer.Option(5, "--choices", "-c", help="Choices per branching event."),
    districts: int = typer.Option(1, "--districts", "-d", help="Initial district count."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="JSON output path."),
) -> None:
    """Simulate choice events on a district graph and emit StreamPackets."""
    from polomni.core.superspace.district_graph import DistrictGraph

    graph = DistrictGraph()
    root_ids = []
    for i in range(districts):
        root_ids.append(
            graph.add_district(
                mass=1.0 + 0.1 * i,
                law_of_gravity=[6.674e-11, 1.1e-52],
                coordinate=[float(i), 0.0, 0.0],
                lambda_vacuum=1.0e-52,
            )
        )

    all_packets = []
    for root in root_ids:
        packets = graph.trigger_choice_event(root, num_choices=choices)
        all_packets.extend(packets)

    table = Table(title="Polomni Simulation")
    table.add_column("District")
    table.add_column("Parent")
    table.add_column("Choices")
    table.add_column("Phi_stream")
    for pkt in all_packets:
        table.add_row(
            str(pkt.district_id),
            str(pkt.parent_id) if pkt.parent_id is not None else "-",
            str(pkt.num_choices),
            f"{sum(pkt.phi_stream) / len(pkt.phi_stream):.4e}",
        )
    console.print(table)
    console.print(f"[green]Spawned {len(all_packets)} stream packets from {districts} root(s).[/green]")

    if output is not None:
        payload = {
            "choices": choices,
            "districts": districts,
            "packets": [p.model_dump() for p in all_packets],
            "graph": graph.to_dict(),
        }
        out_path = Path(output)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"Wrote {out_path}")


@app.command("batch")
def batch_run(
    seeds: str = typer.Option("0,1,2,3,4", "--seeds", help="Comma-separated RNG seeds."),
    count: int = typer.Option(0, "--count", help="If >0, use seeds 0..count-1 instead."),
    choices: int = typer.Option(5, "--choices", "-c"),
    districts: int = typer.Option(1, "--districts", "-d"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="JSON output directory."),
) -> None:
    """Run district simulations across multiple seeds."""
    from polomni.core.simulation.batch import run_batch_simulation

    if count > 0:
        seed_list = list(range(count))
    else:
        seed_list = [int(s.strip()) for s in seeds.split(",") if s.strip()]

    results = run_batch_simulation(seed_list, choices=choices, districts=districts)
    table = Table(title="Batch Simulation")
    table.add_column("Seed")
    table.add_column("Packets")
    table.add_column("Nodes")
    table.add_column("Edges")
    for row in results:
        table.add_row(
            str(row["seed"]),
            str(row["packets_spawned"]),
            str(row["graph_nodes"]),
            str(row["graph_edges"]),
        )
    console.print(table)

    if output is not None:
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "batch_results.json"
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        console.print(f"Wrote {path}")
