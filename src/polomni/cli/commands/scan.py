"""CMB scar scan command."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from polomni.observatory.ingest.healpix_loader import load_healpix_map, synthetic_cmb_map
from polomni.observatory.reports.detection_report import format_report, save_json
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import compute_rble_signature

app = typer.Typer(help="Run CMB RBLE scar scan.")
console = Console()

# Real-universe CMB products we can scan without multi-GB downloads.
UNIVERSE_MAP_PRODUCTS: tuple[str, ...] = (
    "wmap_k_band",
    "wmap_q_band",
    "wmap_v_band",
    "planck_smica_cmb",
)


def _run_detection(cmb, *, nside: int, seed: int, nulls: int, hierarchical: bool, neural: bool):
    if hierarchical:
        from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search

        detection = hierarchical_sky_search(
            cmb, coarse_nside=min(16, nside), seed=seed, neural_prescreen=neural
        )
    else:
        detection = compute_rble_signature(cmb)

    null_maps = generate_null_ensemble(nulls, nside, seed=seed + 1)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]
    mu = float(sum(null_scores) / len(null_scores))
    sigma = float((sum((s - mu) ** 2 for s in null_scores) / len(null_scores)) ** 0.5)
    if sigma > 0:
        detection.null_sigma = (detection.rble_score - mu) / sigma
    return detection


def _detection_payload(detection) -> dict:
    if hasattr(detection, "model_dump"):
        return detection.model_dump(mode="json")
    if hasattr(detection, "to_dict"):
        return detection.to_dict()
    return {
        "rble_score": float(detection.rble_score),
        "null_sigma": getattr(detection, "null_sigma", None),
        "preferred_axis": list(getattr(detection, "preferred_axis", [])),
    }


def _neural_approx(cmb) -> float | None:
    try:
        from polomni.neural.scar_classifier.rble_scanner import score_map

        return float(score_map(cmb))
    except Exception:
        return None


def _load_real_map(map_product: str, nside: int):
    from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map
    from polomni.observatory.pipeline.cache import DataCache
    from polomni.observatory.pipeline.catalog import get_product
    from polomni.observatory.pipeline.downloader import fetch_product

    cache = DataCache()
    product = get_product(map_product)
    fetched = fetch_product(product, cache)
    raw = load_healpix_map(fetched.path, field="T")
    cmb = downsample_map(raw, nside)
    return cmb, fetched


@app.callback(invoke_without_command=True)
def scan_run(
    map_path: str | None = typer.Option(
        None, "--map", "-m", help="HEALPix FITS or .npy path (default: synthetic)."
    ),
    real_data: bool = typer.Option(
        False, "--real", help="Use cached WMAP/Planck map from polomni data pipeline."
    ),
    map_product: str = typer.Option(
        "wmap_k_band", "--map-product", help="Data product ID when --real is set."
    ),
    universe: bool = typer.Option(
        False,
        "--universe",
        help="Scan all cached real CMB bands (WMAP K/Q/V + Planck SMICA).",
    ),
    nside: int = typer.Option(64, "--nside", help="NSIDE for synthetic or downsampled real map."),
    seed: int = typer.Option(42, "--seed", help="RNG seed."),
    nulls: int = typer.Option(20, "--nulls", help="Null ensemble size for significance."),
    report: str | None = typer.Option(None, "--report", "-r", help="JSON report output."),
    neural: bool = typer.Option(
        False, "--neural", help="Also score with neural/heuristic scar classifier."
    ),
    hierarchical: bool = typer.Option(
        False, "--hierarchical", help="Use coarse-to-fine hierarchical sky search."
    ),
) -> None:
    """Scan a CMB map for RBLE scar signatures."""
    if universe:
        rows: list[dict] = []
        for pid in UNIVERSE_MAP_PRODUCTS:
            try:
                cmb, fetched = _load_real_map(pid, nside)
            except Exception as exc:
                console.print(f"[yellow]skip {pid}[/yellow]: {exc}")
                continue
            console.print(
                f"[bold]Universe scan[/bold] {pid} "
                f"({'network' if fetched.downloaded else 'cache'}) NSIDE={nside}"
            )
            detection = _run_detection(
                cmb,
                nside=nside,
                seed=seed,
                nulls=nulls,
                hierarchical=hierarchical,
                neural=neural,
            )
            console.print(format_report(detection))
            neural_score = _neural_approx(cmb) if neural else None
            if neural_score is not None:
                console.print(f"[dim]Neural approx S_RBLE: {neural_score:.4f}[/dim]")
            rows.append(
                {
                    "map_product_id": pid,
                    "nside": nside,
                    "source": str(fetched.path),
                    "from_cache": fetched.from_cache,
                    "detection": _detection_payload(detection),
                    "neural_approx_s_rble": neural_score,
                }
            )

        table = Table(title="Universe multi-map RBLE scan")
        table.add_column("Map")
        table.add_column("S_RBLE")
        table.add_column("σ_null")
        table.add_column("Neural")
        for r in rows:
            det = r["detection"]
            table.add_row(
                r["map_product_id"],
                f"{det.get('rble_score', float('nan')):.4g}",
                f"{det.get('null_sigma', float('nan')):.2f}"
                if det.get("null_sigma") is not None
                else "—",
                f"{r['neural_approx_s_rble']:.4f}"
                if r.get("neural_approx_s_rble") is not None
                else "—",
            )
        console.print(table)

        out_path = Path(report) if report else Path("data/reports/universe_multi_map_scan.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "study_id": "universe_multi_map_scan",
                    "nside": nside,
                    "hierarchical": hierarchical,
                    "neural": neural,
                    "maps": rows,
                    "caveat": (
                        "Computational scan of public CMB products — not a claimed "
                        "multiverse detection."
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        console.print(f"[green]Wrote {out_path}[/green]")
        return

    if real_data:
        cmb, fetched = _load_real_map(map_product, nside)
        console.print(
            f"[dim]Real data: {map_product} → NSIDE={nside} "
            f"({'network' if fetched.downloaded else 'cache'})[/dim]"
        )
    elif map_path is not None:
        cmb = load_healpix_map(Path(map_path), field="T")
    else:
        cmb = synthetic_cmb_map(nside, seed=seed)
        console.print(f"[dim]Using synthetic CMB map NSIDE={nside}, seed={seed}[/dim]")

    detection = _run_detection(
        cmb,
        nside=nside,
        seed=seed,
        nulls=nulls,
        hierarchical=hierarchical,
        neural=neural,
    )
    console.print(format_report(detection))

    if neural:
        approx = _neural_approx(cmb)
        if approx is not None:
            console.print(f"[dim]Neural approx S_RBLE: {approx:.4f}[/dim]")

    if report is not None:
        path = save_json(detection, Path(report))
        console.print(f"[green]Report saved to {path}[/green]")
