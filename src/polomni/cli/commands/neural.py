"""Neural training CLI for loop corpus and Graph-NODE predictors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from rich.console import Console
from rich.table import Table

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.closed_loop import run_closed_loop
from polomni.neural.datasets.loop_corpus import DEFAULT_LOOP_RUNS_DIR, load_corpus
from polomni.neural.guidance import NeuralGuidance
from polomni.neural.scar_classifier.train_scar import train_scar_classifier
from polomni.neural.train import (
    DEFAULT_CHECKPOINT_DIR,
    train_axis_predictor,
    train_branch_predictor,
)

app = typer.Typer(help="Train and evaluate Graph-NODE / scar neural models.")
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
            f"[yellow]No samples in {corpus_dir} — run: bash scripts/build-corpus.sh 50[/yellow]"
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
    with_scar: Annotated[
        bool,
        typer.Option("--with-scar/--no-scar", help="Also train scar classifier."),
    ] = True,
    seed: Annotated[int, typer.Option("--seed", help="Weight initialization seed.")] = 0,
) -> None:
    """Train Graph-NODE axis/branch predictors (+ optional scar classifier)."""
    corpus = load_corpus(corpus_dir)
    if corpus.n_samples == 0:
        console.print(f"[red]Empty corpus at {corpus_dir}[/red]")
        raise typer.Exit(1)

    console.print(
        f"[dim]Training on {corpus.n_samples} samples "
        f"({corpus.summary()['n_runs']} runs), epochs={epochs}[/dim]"
    )

    results: dict[str, dict] = {}
    try:
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
        if with_scar and not axis_only and not branch_only:
            results["scar"] = train_scar_classifier(
                corpus,
                epochs=max(40, epochs // 2),
                seed=seed,
                checkpoint_dir=checkpoint_dir,
            )
    except Exception as exc:
        console.print(f"[red]Training error: {exc}[/red]")
        raise typer.Exit(1) from exc

    for name, report in results.items():
        if not report.get("trained"):
            console.print(f"[red]{name}: {report.get('reason', 'failed')}[/red]")
            continue
        console.print(
            f"[green]{name}[/green] "
            f"backend={report['backend']} "
            f"loss={report['final_loss']:.6f} "
            f"checkpoint={report['checkpoint']}"
        )
        if "mean_axis_error_deg" in report:
            console.print(f"  mean_axis_error_deg={report['mean_axis_error_deg']:.3f}")


@app.command("status")
def neural_status(
    checkpoint_dir: Annotated[
        Path,
        typer.Option("--checkpoint-dir"),
    ] = DEFAULT_CHECKPOINT_DIR,
) -> None:
    """Show which neural checkpoints are available."""
    g = NeuralGuidance(checkpoint_dir=checkpoint_dir)
    scar = (checkpoint_dir / "scar_classifier.npz").is_file() or (
        checkpoint_dir / "scar_classifier.pt"
    ).is_file()
    console.print(json.dumps({**g.status(), "scar": scar}, indent=2))


@app.command("evaluate")
def neural_evaluate(
    steps: Annotated[int, typer.Option("--steps")] = 4,
    trials: Annotated[int, typer.Option("--trials")] = 3,
    nside: Annotated[int, typer.Option("--nside")] = 32,
    seed: Annotated[int, typer.Option("--seed")] = 0,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Compare Graph-NODE (NEURAL) closed-loop vs uniform / axis_biased baselines."""
    arms = {
        "uniform": ChoicePolicy.UNIFORM,
        "axis_biased": ChoicePolicy.AXIS_BIASED,
        "neural": ChoicePolicy.NEURAL,
    }
    summary: dict[str, dict] = {}
    for name, policy in arms.items():
        finals: list[float] = []
        means: list[float] = []
        for t in range(trials):
            _, results = run_closed_loop(
                steps=steps,
                nside=nside,
                seed=seed + 1000 * t,
                policy=policy,
            )
            errs = [r.axis_error_deg for r in results]
            finals.append(errs[-1])
            means.append(float(np.mean(errs)))
        summary[name] = {
            "final_axis_error_deg": float(np.mean(finals)),
            "mean_axis_error_deg": float(np.mean(means)),
            "trials": trials,
        }

    improvement = (
        summary["uniform"]["final_axis_error_deg"] - summary["neural"]["final_axis_error_deg"]
    )
    payload = {
        "summary": summary,
        "neural_vs_uniform_deg": improvement,
        "neural_wins": improvement > 0.5,
        "guidance": NeuralGuidance().status(),
    }
    if as_json:
        console.print(json.dumps(payload, indent=2))
        return

    table = Table(title="Neural closed-loop evaluation")
    table.add_column("Policy")
    table.add_column("Final err°")
    table.add_column("Mean err°")
    for name, row in summary.items():
        table.add_row(
            name,
            f"{row['final_axis_error_deg']:.2f}",
            f"{row['mean_axis_error_deg']:.2f}",
        )
    console.print(table)
    style = "green" if payload["neural_wins"] else "yellow"
    console.print(
        f"[{style}]neural vs uniform: {improvement:+.2f}° "
        f"(wins={payload['neural_wins']})[/{style}]"
    )
    if not payload["guidance"]["ready"]:
        console.print(
            "[dim]No Graph-NODE checkpoints — neural arm falls back to axis_biased. "
            "Run: bash scripts/build-corpus.sh 50 && bash scripts/train-neural.sh[/dim]"
        )


@app.command("measure-axis")
def neural_measure_axis(
    map_product: Annotated[str, typer.Option("--map-product")] = "wmap_k_band",
    nside: Annotated[int, typer.Option("--nside")] = 32,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Freeze and print the *real* hierarchical preferred axis on a cached CMB map."""
    from polomni.integration.real_sky_bridge import measure_preferred_axis
    from polomni.observatory.pipeline.cache import DataCache

    m = measure_preferred_axis(DataCache(), map_product, nside)
    payload = m.to_dict()
    if as_json:
        console.print(json.dumps(payload, indent=2))
        return
    console.print(
        f"[bold]Real preferred axis[/bold] ({m.map_product_id}, nside={m.nside})\n"
        f"  provenance={payload['provenance']}  method={m.method}\n"
        f"  source={m.source_path}\n"
        f"  axis={m.axis}\n"
        f"  lon={m.lon_deg:.3f}°  lat={m.lat_deg:.3f}°\n"
        f"  S_RBLE={m.rble_score:.4g}"
    )


@app.command("finetune-real")
def neural_finetune_real(
    count: Annotated[int, typer.Option("--count", help="Physics-loop runs to log.")] = 20,
    steps: Annotated[int, typer.Option("--steps")] = 3,
    nside: Annotated[int, typer.Option("--nside")] = 32,
    map_product: Annotated[str, typer.Option("--map-product")] = "wmap_k_band",
    epochs: Annotated[int, typer.Option("--epochs")] = 80,
    seed: Annotated[int, typer.Option("--seed")] = 0,
) -> None:
    """Fine-tune Graph-NODE on real-sky axis targets, then ready for `neural probe`."""
    from polomni.neural.finetune_real import fine_tune_on_real_sky

    console.print(
        f"[dim]Generating {count} real-sky target runs on {map_product} "
        f"(nside={nside})…[/dim]"
    )
    reports = fine_tune_on_real_sky(
        count=count,
        steps=steps,
        nside=nside,
        map_product_id=map_product,
        epochs=epochs,
        seed=seed,
    )
    console.print(
        f"[green]Fine-tune complete[/green] — "
        f"{reports['n_samples_total']} samples, "
        f"axis_err={reports['axis'].get('mean_axis_error_deg', 'n/a')}, "
        f"scar_err={reports['scar'].get('mean_axis_error_deg', 'n/a')}"
    )
    console.print("[dim]Next: poetry run polomni neural probe[/dim]")


@app.command("probe")
def neural_probe(
    map_product: Annotated[
        str, typer.Option("--map-product", help="Cached CMB product.")
    ] = "wmap_k_band",
    nside: Annotated[int, typer.Option("--nside")] = 32,
    steps: Annotated[int, typer.Option("--steps")] = 4,
    seed: Annotated[int, typer.Option("--seed")] = 0,
    out: Annotated[
        Path,
        typer.Option("--out", help="Write JSON report."),
    ] = Path("data/reports/m2_neural_real_sky_probe.json"),
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """M2: neural physics-loop vs baselines on real cached sky (multiverse probe)."""
    from polomni.neural.multiverse_probe import run_multiverse_probe, write_probe_report

    report = run_multiverse_probe(
        map_product_id=map_product,
        nside=nside,
        steps=steps,
        seed=seed,
    )
    path = write_probe_report(report, out)
    payload = report.to_dict()
    if as_json:
        console.print(json.dumps(payload, indent=2))
        return

    table = Table(title=f"M2 Neural Real-Sky Probe ({map_product})")
    table.add_column("Arm")
    table.add_column("Final sep°")
    table.add_column("Mean sep°")
    table.add_column("Final align")
    for name, arm in report.arms.items():
        table.add_row(
            name,
            f"{arm.final_separation_deg:.2f}",
            f"{arm.mean_separation_deg:.2f}",
            f"{arm.final_alignment:.4f}",
        )
    console.print(table)
    style = "green" if report.neural_beats_uniform else "yellow"
    console.print(f"[{style}]{report.claim}[/{style}]")
    if report.preferred_axis:
        pa = report.preferred_axis
        console.print(
            f"[bold]Frozen real axis[/bold] lon={pa.get('lon_deg'):.2f}° "
            f"lat={pa.get('lat_deg'):.2f}°  "
            f"S_RBLE={pa.get('rble_score'):.4g}  "
            f"source={pa.get('source_path')}"
        )
    if report.neural_prescreen_sep_deg is not None:
        console.print(
            f"[dim]Scar-classifier vs hierarchical axis: "
            f"{report.neural_prescreen_sep_deg:.2f}°[/dim]"
        )
    for c in report.caveats:
        console.print(f"[dim]• {c}[/dim]")
    console.print(f"[dim]Wrote {path}[/dim]")
