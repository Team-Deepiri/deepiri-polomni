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

    failed: list[str] = []
    for pid in dict.fromkeys(ids):
        product = get_product(pid)
        console.print(f"[cyan]Fetching[/cyan] {product.name}…")
        try:
            result = fetch_product(product, cache, force=force)
        except Exception as exc:
            failed.append(pid)
            console.print(f"  [yellow]✗[/yellow] {pid}: {exc}")
            continue
        src = "cache" if result.from_cache and not result.downloaded else "network"
        console.print(f"  → {result.path} ({result.bytes_written / 1024:.1f} KiB, {src})")

    if failed:
        console.print(
            f"[yellow]{len(failed)} product(s) failed[/yellow] ({', '.join(failed)}); "
            "required maps: wmap_k_band, planck_smica_cmb"
        )

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


@app.command("worlds")
def worlds(
    nside: Annotated[int, typer.Option("--nside", help="HEALPix NSIDE for density scan.")] = 32,
    weight: Annotated[
        str, typer.Option("--weight", help="Density weight: count | teff | period.")
    ] = "count",
    ensemble: Annotated[
        int, typer.Option("--ensemble", help="Footprint-matched null ensemble size.")
    ] = 40,
    n_null: Annotated[
        int, typer.Option("--null", help="Power-spectrum null ensemble size.")
    ] = 100,
) -> None:
    """Scan the real NASA exoplanet sky with RBLE + footprint-matched null."""
    from polomni.viz.cosmos.worlds import exoplanet_world_payload

    payload = exoplanet_world_payload(
        nside=nside, weight=weight, n_ensemble=ensemble, n_null=n_null
    )
    scan = payload["scan"]
    align = payload["alignment"]
    dipole = payload["dipole"]
    spectrum = payload["spectrum"]
    cat = payload["catalog"]

    table = Table(title=f"World Atlas — NASA Exoplanet Archive (NSIDE {nside}, {weight})")
    table.add_column("Quantity")
    table.add_column("Value")
    rows = [
        ("Worlds", f"{cat['n_worlds']} confirmed ({cat['n_hosts']} host stars)"),
        ("Sky occupancy", f"{cat['occupied_pixels']} px ({cat['occupancy_fraction']:.1%} of sky)"),
        ("S_RBLE (geodesic Radon)", f"{scan['rble_score']:.4f}"),
        ("Preferred axis", f"[{', '.join(f'{v:.3f}' for v in scan['preferred_axis'])}]"),
        (
            "Footprint-matched null",
            f"μ={scan['null_mu']:.4f} σ={scan['null_sigma']:.4f} → "
            f"{scan['null_sigma_significance']:+.2f}σ",
        ),
        ("Alignment order S", f"{align['order_parameter_s']:.4f} (isotropic → 0)"),
        ("Tr(Q) invariant", f"{align['trace']:.6f}"),
        ("Nematic eigenvalues", f"{', '.join(f'{v:.4f}' for v in align['eigenvalues'])}"),
        (
            "Axis ↔ Galactic pole",
            f"{scan['separation_from_galactic_pole_deg']:.1f}° (90° = in-plane)",
        ),
    ]
    for name, value in rows:
        table.add_row(name, value)
    console.print(table)

    d_table = Table(title="World dipole — cosmic-rest-frame test")
    d_table.add_column("Quantity")
    d_table.add_column("Value")
    refs = dipole["references"]
    d_rows = [
        ("Dipole magnitude |⟨n⟩|", f"{dipole['magnitude']:.4f} (0 = isotropic)"),
        ("Bootstrap 68% cone", f"{dipole['bootstrap']['sigma68_deg']:.1f}°"),
        ("↔ Kepler field", f"{refs['kepler_field_center']['separation_deg']:.1f}°"),
        ("↔ CMB dipole apex", f"{refs['CMB_dipole_apex']['separation_deg']:.1f}°"),
        ("↔ Ecliptic pole", f"{refs['ecliptic_north_pole']['separation_deg']:.1f}°"),
        ("↔ Galactic pole", f"{refs['galactic_north_pole']['separation_deg']:.1f}°"),
    ]
    for name, value in d_rows:
        d_table.add_row(name, value)
    console.print(d_table)

    excision = dipole["kepler_excision"]
    ex_table = Table(title="Kepler-excision scan — dipole vs removed footprint")
    ex_table.add_column("Cut radius")
    ex_table.add_column("N left")
    ex_table.add_column("|dipole|")
    ex_table.add_column("iso. expect.")
    ex_table.add_column("↔ Kepler")
    ex_table.add_column("↔ CMB apex")
    ex_table.add_row(
        "full",
        str(excision["n_worlds_full"]),
        f"{excision['full_magnitude']:.3f}",
        f"{excision['full_isotropic_expectation']:.3f}",
        f"{dipole['references']['kepler_field_center']['separation_deg']:.1f}°",
        f"{dipole['references']['CMB_dipole_apex']['separation_deg']:.1f}°",
    )
    for row in excision["rows"]:
        ex_table.add_row(
            f">{row['radius_deg']:.0f}°",
            str(row["n_worlds"]),
            f"{row['magnitude']:.3f}",
            f"{row['isotropic_expectation']:.3f}",
            f"{row['references']['kepler_field_center']:.1f}°",
            f"{row['references']['CMB_dipole_apex']:.1f}°",
        )
    console.print(ex_table)
    console.print(
        "[dim]If the dipole collapses toward the isotropic expectation as the Kepler "
        "field is cut out, the 'scar' was the footprint, not physics.[/dim]"
    )

    s_table = Table(title="World-sky power spectrum (uniform-within-footprint null)")
    s_table.add_column("ℓ")
    s_table.add_column("C_ℓ")
    s_table.add_column("null p50")
    s_table.add_column("null [16,84]")
    s_table.add_column("z")
    s_table.add_column("p-value")
    ell = spectrum["ell"]
    for l, c, p50, p16, p84, z, pv in zip(
        ell,
        spectrum["pseudo"],
        spectrum["null"]["p50"],
        spectrum["null"]["p16"],
        spectrum["null"]["p84"],
        spectrum["null"]["z_score"],
        spectrum["null"]["p_value"],
    ):
        if l > 12:
            continue
        s_table.add_row(
            str(l),
            f"{c:.2e}",
            f"{p50:.2e}",
            f"[{p16:.1e},{p84:.1e}]",
            f"{z:+.2f}",
            f"{pv:.3f}",
        )
    console.print(s_table)
    console.print(
        "[dim]Only multipoles clearing the null (small p, |z| beyond scatter) deserve a "
        "physical reading; the low-ℓ band is dominated by the fixed footprint.[/dim]"
    )

    methods = payload["methods"]
    if methods:
        m_table = Table(title="Per-method axis audit (selection-bias check)")
        m_table.add_column("Method")
        m_table.add_column("N")
        m_table.add_column("S (order)")
        m_table.add_column("Axis")
        m_table.add_column("↔ Gal. pole")
        for method, info in methods.items():
            m_table.add_row(
                method,
                str(info["n_worlds"]),
                f"{info['order_parameter_s']:.3f}",
                f"[{', '.join(f'{v:.2f}' for v in info['preferred_axis'])}]",
                f"{info['separation_from_galactic_pole_deg']:.0f}°",
            )
        console.print(m_table)
    if cat["methods"]:
        console.print(f"[dim]Discovery methods: {', '.join(cat['methods'])}[/dim]")
    console.print("[dim]A genuine scar must survive the footprint null AND persist across methods.[/dim]")


@app.command("cross-sky")
def cross_sky(
    min_objects: Annotated[
        int, typer.Option("--min-objects", help="Min objects for a sky to count.")
    ] = 20,
) -> None:
    """Compare world dipoles across independent skies (the two-sky test)."""
    from polomni.observatory.pipeline.sources.cross_sky import cross_sky_report

    report = cross_sky_report(min_objects=min_objects)
    skies = report["skies"]
    if not skies:
        console.print("[yellow]No cached sky datasets found. Run `polomni data fetch` first.[/yellow]")
        return

    table = Table(title="Cross-sky dipole comparison (independent skies)")
    table.add_column("Sky")
    table.add_column("N")
    table.add_column("|dipole|")
    table.add_column("iso expect")
    table.add_column("↔ CMB apex")
    table.add_column("↔ Kepler")
    table.add_column("↔ Ecliptic")
    table.add_column("↔ Gal. pole")
    for s in skies:
        m = s.get("magnitude")
        refs = s.get("references") or {}
        table.add_row(
            s["sky"],
            str(s["n_objects"]),
            f"{m:.3f}" if m is not None else "—",
            f"{s['isotropic_expectation']:.3f}" if s.get("isotropic_expectation") else "—",
            f"{refs['CMB_dipole_apex']['separation_deg']:.1f}°" if "CMB_dipole_apex" in refs else "—",
            f"{refs['kepler_field_center']['separation_deg']:.1f}°" if "kepler_field_center" in refs else "—",
            f"{refs['ecliptic_north_pole']['separation_deg']:.1f}°" if "ecliptic_north_pole" in refs else "—",
            f"{refs['galactic_north_pole']['separation_deg']:.1f}°" if "galactic_north_pole" in refs else "—",
        )
    console.print(table)

    pairs = report["pairwise"]
    if pairs:
        p_table = Table(title="Pairwise axis separations")
        p_table.add_column("Sky A")
        p_table.add_column("Sky B")
        p_table.add_column("Separation (°)")
        for p in pairs:
            p_table.add_row(p["sky_a"], p["sky_b"], f"{p['separation_deg']:.1f}")
        console.print(p_table)
    console.print(
        "[dim]A genuine scar must point at the SAME axis in every unrelated sky; "
        "dipoles that disagree across skies are survey footprints, not physics.[/dim]"
    )


@app.command("bubble")
def bubble(
    nside: Annotated[int, typer.Option("--nside", help="Map resolution.")] = 128,
    n_null: Annotated[int, typer.Option("--n-null", help="Null realizations.")] = 16,
    n_null_rank1: Annotated[int, typer.Option("--n-null-rank1", help="Rank-1 null realizations.")] = 16,
) -> None:
    """Search a real CMB map for bubble collisions (two complementary statistics)."""
    from polomni.observatory.pipeline.sources.bubble_collisions import bubble_collision_report

    rep = bubble_collision_report(nside=nside, n_null=n_null, n_null_rank1=n_null_rank1)

    header = Table(title="Bubble-collision search — eternal-inflation signature")
    header.add_column("Field")
    header.add_column("Value")
    for key, val in [
        ("Map", rep["map_product_id"]),
        ("Circles scanned", str(rep["n_circles_scanned"])),
        ("Mask (f_sky)", f"{rep['mask']['f_sky']:.3f} @ |b|≥{rep['mask']['b_cut_deg']}°"),
        ("Observed max edge", f"{rep['null']['max_abs_edge_uk']['observed']:.1f} µK"),
        ("Null median", f"{rep['null']['max_abs_edge_uk']['median']:.1f} µK"),
        ("p-value", f"{rep['p_value']:.4f}"),
        ("Verdict", rep["verdict"]),
    ]:
        header.add_row(key, val)
    console.print(header)

    if rep["top_candidates"]:
        t = Table(title="Top candidate circles")
        t.add_column("gal lon")
        t.add_column("gal lat")
        t.add_column("Radius")
        t.add_column("Edge (µK)")
        for c in rep["top_candidates"][:6]:
            t.add_row(
                f"{c['gal_lon']:.1f}°",
                f"{c['gal_lat']:.1f}°",
                f"{c['radius_deg']:.0f}°",
                f"{c['edge_uk']:.2f}",
            )
        console.print(t)

    sc = rep["strongest_circle"]
    if sc.get("radial_profile"):
        prof = Table(title=f"Radial profile of strongest circle @ ({sc['gal_lon']}°, {sc['gal_lat']}°)")
        prof.add_column("Radius (°)")
        prof.add_column("Mean T (µK)")
        for row in sc["radial_profile"]:
            if row["n_pixels"] == 0:
                continue
            prof.add_row(f"{row['radius_deg']:.1f}", f"{row['mean_t_uk']:.2f}")
        console.print(prof)
    console.print(
        "[dim]A collision is a STEP: flat inside, flat outside, one sharp edge. "
        "A smooth gradient is not a bubble.[/dim]"
    )

    ha = rep.get("harmonic_axis") or {}
    if ha:
        ha_table = Table(title="Rank-1 harmonic axis search")
        ha_table.add_column("Field")
        ha_table.add_column("Value")
        for key, val in [
            ("Axis (gal)", f"({ha['axis']['gal_lon']}°, {ha['axis']['gal_lat']}°)"),
            ("Score", str(ha["score"])),
            ("Null median (max score)", str(ha["null"]["max_score_median"])),
            ("p-value", str(ha["p_value"])),
            ("Verdict", ha["verdict"]),
        ]:
            ha_table.add_row(key, val)
        console.print(ha_table)
        console.print(
            "[dim]Rank-1 invariant: a collision about n̂_c gives a_lm = C_l·Y_lm(n̂_c) "
            "at every l, so m=0 power fraction at the axis is 1 per multipole "
            "(isotropic: 1/(2l+1)). The CMB's own 'axis of evil' is the null, "
            "not a detection.[/dim]"
        )


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
