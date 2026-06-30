"""Neural training CLI for loop corpus and Graph-NODE predictors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from polomni.neural.datasets.loop_corpus import DEFAULT_LOOP_RUNS_DIR, load_corpus
from polomni.neural.train import (
    DEFAULT_CHECKPOINT_DIR,
    train_axis_predictor,
    train_branch_predictor,
)

app = typer.Typer(help="Train neural predictors on closed-loop telemetry.")
console = Console()


@app.command("corpus")
def corpus_stats(
    corpus_dir: Annotated[
        Path,
        typer.Option("--corpus", help="Directory of loop-run JSON files."),
    ] = DEFAULT_LOOP_RUNS_DIR,
    as_json: Annotated[bool, typer.Option("--json", help="Output JSON only.")] = False,
) -> None:
    """Summarize loop-run training corpus statistics."""
    corpus = load_corpus(corpus_dir)
    summary = corpus.summary()

    if as_json:
        console.print(json.dumps(summary, indent=2))
        return

    table = Table(title="Loop Corpus")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in summary.items():
        table.add_row(key, str(value))
    console.print(table)

    if corpus.n_samples == 0:
        console.print(
            f"[yellow]No samples in {corpus_dir} — run closed-loop batches to populate JSON runs.[/yellow]"
        )


@app.command("train")
def neural_train(
    corpus_dir: Annotated[
        Path,
        typer.Option("--corpus", help="Directory of loop-run JSON files."),
    ] = DEFAULT_LOOP_RUNS_DIR,
    epochs: Annotated[int, typer.Option("--epochs", help="Training epochs per predictor.")] = 100,
    checkpoint_dir: Annotated[
        Path,
        typer.Option("--checkpoint-dir", help="Checkpoint output directory."),
    ] = DEFAULT_CHECKPOINT_DIR,
    axis_only: Annotated[bool, typer.Option("--axis-only", help="Train axis predictor only.")] = False,
    branch_only: Annotated[
        bool,
        typer.Option("--branch-only", help="Train branch predictor only."),
    ] = False,
    seed: Annotated[int, typer.Option("--seed", help="Weight initialization seed.")] = 0,
) -> None:
    """Train Graph-NODE axis and branch predictors on the loop corpus."""
    corpus = load_corpus(corpus_dir)
    if corpus.n_samples == 0:
        console.print(f"[red]Empty corpus at {corpus_dir}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[dim]Training on {corpus.n_samples} samples "
        f"({corpus.summary()['n_runs']} runs), epochs={epochs}[/dim]"
    )

    results: dict[str, dict] = {}
    if not branch_only:
        results["axis"] = train_axis_predictor(
            corpus,
            epochs=epochs,
            seed=seed,
            checkpoint_dir=checkpoint_dir,
        )
    if not axis_only:
        results["branch"] = train_branch_predictor(
            corpus,
            epochs=epochs,
            seed=seed,
            checkpoint_dir=checkpoint_dir,
        )

    for name, report in results.items():
        if not report.get("trained"):
            console.print(f"[red]{name} predictor: {report.get('reason', 'failed')}[/red]")
            continue
        console.print(
            f"[green]{name} predictor[/green] "
            f"backend={report['backend']} "
            f"loss={report['final_loss']:.6f} "
            f"checkpoint={report['checkpoint']}"
        )
        if name == "axis":
            console.print(f"  mean_axis_error_deg={report['mean_axis_error_deg']:.3f}")
