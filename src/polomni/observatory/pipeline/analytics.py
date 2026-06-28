"""Analytics helpers for cached cosmology data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import calibrate_from_power_spectrum, correlate_gw_rble
from polomni.observatory.pipeline.sources.gwosc import load_cached_gwtc
from polomni.observatory.reports.comparison import latest_report, load_report
from polomni.viz.gw_timeline import plot_gw_timeline
from polomni.viz.power_spectrum import plot_power_spectrum


def plot_cached_power_spectrum(
    cache: DataCache | None = None,
    *,
    product_id: str = "planck_cmb_tt_power",
    output_path: str | Path | None = None,
) -> Path:
    cache = cache or DataCache()
    ell, dl = calibrate_from_power_spectrum(cache, product_id=product_id)
    return plot_power_spectrum(
        ell,
        dl,
        title=f"CMB TT Power — {product_id}",
        save_path=output_path or Path("data/figures") / f"{product_id}.png",
    )


def plot_cached_gw_timeline(
    cache: DataCache | None = None,
    *,
    output_path: str | Path | None = None,
    limit: int = 50,
) -> Path:
    cache = cache or DataCache()
    snap = load_cached_gwtc(cache)
    events = [e.model_dump() for e in snap.events[:limit]]
    return plot_gw_timeline(
        events,
        save_path=output_path or Path("data/figures/gw_timeline.png"),
        limit=limit,
    )


def summarize_gw_rble_correlation(
    cache: DataCache | None = None,
    *,
    report_path: str | Path | None = None,
    max_separation_deg: float = 30.0,
) -> list[dict[str, Any]]:
    cache = cache or DataCache()
    if report_path is None:
        latest = latest_report()
        if latest is None:
            return []
        report_path = latest
    report = load_report(report_path)
    snap = load_cached_gwtc(cache)
    return correlate_gw_rble(
        report.preferred_axis,
        snap.events,
        max_separation_deg=max_separation_deg,
    )
