"""CMB scar scan command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from polomni.observatory.ingest.healpix_loader import load_healpix_map, synthetic_cmb_map
from polomni.observatory.reports.detection_report import format_report, save_json
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.rble_signature import compute_rble_signature

app = typer.Typer(help="Run CMB RBLE scar scan.")
console = Console()


@app.callback(invoke_without_command=True)
def scan_run(
    map_path: Optional[str] = typer.Option(
        None, "--map", "-m", help="HEALPix FITS or .npy path (default: synthetic)."
    ),
    real_data: bool = typer.Option(
        False, "--real", help="Use cached WMAP/Planck map from polomni data pipeline."
    ),
    map_product: str = typer.Option(
        "wmap_k_band", "--map-product", help="Data product ID when --real is set."
    ),
    nside: int = typer.Option(64, "--nside", help="NSIDE for synthetic or downsampled real map."),
    seed: int = typer.Option(42, "--seed", help="RNG seed."),
    nulls: int = typer.Option(20, "--nulls", help="Null ensemble size for significance."),
    report: Optional[str] = typer.Option(None, "--report", "-r", help="JSON report output."),
    neural: bool = typer.Option(
        False, "--neural", help="Also score with neural/heuristic scar classifier."
    ),
    hierarchical: bool = typer.Option(
        False, "--hierarchical", help="Use coarse-to-fine hierarchical sky search."
    ),
) -> None:
    """Scan a CMB map for RBLE scar signatures."""
    if real_data:
        from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map
        from polomni.observatory.pipeline.cache import DataCache
        from polomni.observatory.pipeline.catalog import get_product
        from polomni.observatory.pipeline.downloader import fetch_product

        cache = DataCache()
        product = get_product(map_product)
        fetched = fetch_product(product, cache)
        raw = load_healpix_map(fetched.path, field="T")
        cmb = downsample_map(raw, nside)
        console.print(
            f"[dim]Real data: {map_product} → NSIDE={nside} "
            f"({'network' if fetched.downloaded else 'cache'})[/dim]"
        )
    elif map_path is not None:
        cmb = load_healpix_map(Path(map_path), field="T")
    else:
        cmb = synthetic_cmb_map(nside, seed=seed)
        console.print(f"[dim]Using synthetic CMB map NSIDE={nside}, seed={seed}[/dim]")

    if hierarchical:
        from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search

        detection = hierarchical_sky_search(cmb, coarse_nside=min(16, nside), seed=seed)
    else:
        detection = compute_rble_signature(cmb)

    null_maps = generate_null_ensemble(nulls, nside if map_path is None else 64, seed=seed + 1)
    null_scores = [compute_rble_signature(m).rble_score for m in null_maps]
    mu = float(sum(null_scores) / len(null_scores))
    sigma = float((sum((s - mu) ** 2 for s in null_scores) / len(null_scores)) ** 0.5)
    if sigma > 0:
        detection.null_sigma = (detection.rble_score - mu) / sigma

    console.print(format_report(detection))

    if neural:
        try:
            from polomni.neural.scar_classifier.rble_scanner import score_map

            approx = score_map(cmb)
            console.print(f"[dim]Neural approx S_RBLE: {approx:.4f}[/dim]")
        except ImportError:
            console.print("[dim]Neural scoring skipped (dependencies unavailable)[/dim]")

    if report is not None:
        path = save_json(detection, Path(report))
        console.print(f"[green]Report saved to {path}[/green]")
