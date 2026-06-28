"""District DAG simulation command."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Run district multiverse simulation.")
console = Console()


@app.callback(invoke_without_command=True)
def run(
    choices: int = typer.Option(5, "--choices", "-c", help="Choices per branching event."),
    districts: int = typer.Option(1, "--districts", "-d", help="Initial district count."),
    output: Path | None = typer.Option(None, "--output", "-o", help="JSON output path."),
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
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"Wrote {output}")
