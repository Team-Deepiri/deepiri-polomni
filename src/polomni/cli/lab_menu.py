"""Interactive lab menu — setup.sh --run and `polomni run` with no subcommand."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer
from rich.console import Console
from rich.table import Table

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.closed_loop import run_closed_loop
from polomni.integration.loop_batch import run_loop_batch
from polomni.integration.loop_logger import log_loop_run
from polomni.integration.multiverse_proof import run_multiverse_proof
from polomni.integration.real_sky_bridge import run_physics_loop
from polomni.integration.workflow import run_lab_workflow
from polomni.math.proofs.base import prove_all
from polomni.neural.datasets.loop_corpus import DEFAULT_LOOP_RUNS_DIR, load_corpus
from polomni.neural.train import DEFAULT_CHECKPOINT_DIR, train_axis_predictor, train_branch_predictor
from polomni.observatory.pipeline.cache import DataCache

console = Console()


def _print_proof_table(report) -> None:
    table = Table(title=f"Multiverse Proof ({report.mode})")
    table.add_column("ID")
    table.add_column("Metric")
    table.add_column("Pass")
    for m in report.metrics:
        table.add_row(m.id, m.name, "✓" if m.passed else "✗")
    console.print(table)
    console.print(
        f"[{'green' if report.all_passed else 'yellow'}]"
        f"{report.pass_rate:.0%} pass in {report.elapsed_seconds:.1f}s[/]"
    )


def _quick_smoke() -> None:
    console.print("[bold]Closed loop[/bold]")
    graph, results = run_closed_loop(steps=3, num_choices=4, nside=32, policy=ChoicePolicy("axis_biased"))
    log_loop_run(graph, results, policy=ChoicePolicy("axis_biased"), nside=32, seed=0)
    console.print(f"  {len(results)} steps, {graph.graph.number_of_nodes()} graph nodes")
    console.print("[bold]Quick proof[/bold]")
    report = run_multiverse_proof(quick=True)
    _print_proof_table(report)


def _full_proof() -> None:
    quick = typer.confirm("Quick mode (~1 min)?", default=True)
    batch = 0
    if typer.confirm("Generate loop corpus first?", default=False):
        batch = int(typer.prompt("Batch run count", default="10"))
    report = run_multiverse_proof(quick=quick, batch_runs=batch)
    _print_proof_table(report)
    out = Path("data/reports/multiverse_proof.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    console.print(f"[green]Wrote {out}[/green]")


def _build_corpus() -> None:
    count = int(typer.prompt("Loop batch count", default="50"))
    nside = int(typer.prompt("NSIDE", default="32"))
    steps = int(typer.prompt("Steps per run", default="3"))
    result = run_loop_batch(
        count=count,
        steps=steps,
        num_choices=4,
        nside=nside,
        policy=ChoicePolicy("axis_biased"),
    )
    console.print(
        f"[green]{result.n_runs} runs[/green] → {result.output_dir}, "
        f"mean axis error={result.mean_final_error_deg:.2f}°"
    )
    corpus = load_corpus(DEFAULT_LOOP_RUNS_DIR)
    console.print(f"Corpus: {corpus.n_samples} samples from {corpus.summary()['n_runs']} runs")


def _train_neural() -> None:
    corpus = load_corpus(DEFAULT_LOOP_RUNS_DIR)
    if corpus.n_samples == 0:
        console.print("[red]Empty corpus — build corpus first (menu option 3).[/red]")
        return
    epochs = int(typer.prompt("Training epochs", default="100"))
    console.print(f"Training on {corpus.n_samples} samples…")
    axis = train_axis_predictor(corpus, epochs=epochs, checkpoint_dir=DEFAULT_CHECKPOINT_DIR)
    branch = train_branch_predictor(corpus, epochs=epochs, checkpoint_dir=DEFAULT_CHECKPOINT_DIR)
    for name, report in [("axis", axis), ("branch", branch)]:
        if report.get("trained"):
            console.print(f"[green]{name}[/green] loss={report['final_loss']:.6f}")


def _lab_workflow() -> None:
    real = typer.confirm("Include real-data pipeline?", default=False)
    result = run_lab_workflow(
        target_nside=64,
        null_ensemble=10,
        fetch_gw=False,
        simulation_choices=4,
        closed_loop_steps=3,
        policy=ChoicePolicy("axis_biased"),
        use_real_data_pipeline=real,
    )
    sim = result.simulation_summary
    console.print(
        f"[green]Done[/green] {sim['graph_nodes']} nodes, "
        f"axis error={sim['final_axis_error_deg']:.2f}°"
    )


def _physics_loop() -> None:
    result = run_physics_loop(steps=3, nside=64, map_product_id="wmap_k_band", cache=DataCache())
    console.print(
        f"Real axis score={result.real_score:.4f}, "
        f"final separation={result.steps[-1].separation_deg:.2f}°"
    )


def _math_prove() -> None:
    suite = prove_all(strict=False, real_data=False)
    passed = sum(1 for r in suite.results if r.passed)
    console.print(f"[green]Math proofs[/green] {passed}/{len(suite.results)} passed")


def _serve_api() -> None:
    import subprocess

    host = typer.prompt("Host", default="127.0.0.1")
    port = int(typer.prompt("Port", default="8091"))
    console.print(f"[dim]Starting API at http://{host}:{port} (Ctrl+C to stop)[/dim]")
    subprocess.run(
        ["poetry", "run", "polomni", "serve", "--host", host, "--port", str(port)],
        check=True,
    )


def _run_all() -> None:
    console.print("[bold]Full lab run — confirm each step[/bold]\n")
    if typer.confirm("1. Math proofs?", default=True):
        _math_prove()
    if typer.confirm("2. Closed loop smoke?", default=True):
        graph, results = run_closed_loop(steps=3, num_choices=4, nside=32, policy=ChoicePolicy("axis_biased"))
        log_loop_run(graph, results, policy=ChoicePolicy("axis_biased"), nside=32, seed=0)
        console.print(f"  {graph.graph.number_of_nodes()} nodes")
    if typer.confirm("3. Multiverse proof (quick)?", default=True):
        report = run_multiverse_proof(quick=True)
        _print_proof_table(report)
    if typer.confirm("4. Build loop corpus? (can take a while)", default=False):
        count = int(typer.prompt("  Batch count", default="10"))
        run_loop_batch(count=count, steps=3, num_choices=4, nside=32, policy=ChoicePolicy("axis_biased"))
    if typer.confirm("5. Train neural predictors?", default=False):
        _train_neural()
    if typer.confirm("6. Physics loop (real-sky bridge)?", default=False):
        _physics_loop()
    if typer.confirm("7. Start API server?", default=False):
        _serve_api()
    console.print("\n[green]Lab run complete.[/green]")


_MENU: list[tuple[str, str, Callable[[], None]]] = [
    ("1", "Quick smoke (closed loop + proof)", _quick_smoke),
    ("2", "Multiverse proof battery", _full_proof),
    ("3", "Build neural corpus (loop batch)", _build_corpus),
    ("4", "Train neural predictors", _train_neural),
    ("5", "Full lab workflow", _lab_workflow),
    ("6", "Physics loop (real-sky bridge)", _physics_loop),
    ("7", "Math proofs", _math_prove),
    ("8", "Serve API", _serve_api),
    ("9", "Run everything (step-by-step prompts)", _run_all),
]


def run_interactive_menu() -> None:
    """Prompt user to pick and run lab workflows."""
    console.print("\n[bold cyan]Polomni Lab[/bold cyan] — interactive runner\n")
    for key, label, _ in _MENU:
        console.print(f"  [bold]{key}[/bold]. {label}")
    console.print("  [bold]0[/bold]. Exit\n")

    choice = typer.prompt("Choose", default="1").strip()
    if choice == "0":
        return

    for key, label, action in _MENU:
        if choice == key:
            console.print(f"\n[bold]→ {label}[/bold]\n")
            try:
                action()
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
            return

    console.print(f"[red]Unknown choice: {choice}[/red]")
    raise typer.Exit(code=1)
