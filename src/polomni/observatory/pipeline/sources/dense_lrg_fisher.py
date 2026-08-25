"""Phase H — denser LRG-class tracer Fisher (SDSS SpecObj RA-strip ingest).

Locksmith: full DESI LRG DR is multi-TB. Outsider loop: SkyServer SpecObj
stratified across RA already gives a CMASS/LRG-like redshift ladder at public
scale (10³–10⁴). Run Fisher on Planck × (PSCz ∪ SDSS-LRG) and measure whether
SNR rises with √N as forecasted — the scaling proof toward bubble_visible.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.dense_tracer import (
    forecast_fisher_snr,
    load_dense_tracer_galactic,
)
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import (
    fisher_scan_report,
)
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic

PRODUCT_ID = "sdss_lrg_dense"


def fetch_sdss_lrg_dense(
    *,
    n_per_strip: int = 250,
    n_strips: int = 36,
    z_lo: float = 0.15,
    z_hi: float = 0.7,
    cache: DataCache | None = None,
    timeout: float = 90.0,
    force: bool = False,
) -> Path:
    """Fetch denser SDSS SpecObj sample (LRG/CMASS-like z) stratified in RA."""
    cache = cache or DataCache()
    dest_dir = cache.root / PRODUCT_ID
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{PRODUCT_ID}.json"
    if dest.exists() and not force:
        entry = cache.get_entry(PRODUCT_ID)
        if entry is not None:
            return dest

    rows: list[dict[str, float]] = []
    width = 360.0 / n_strips
    for i in range(n_strips):
        ra0 = i * width
        ra1 = ra0 + width
        cmd = (
            f"SELECT TOP {n_per_strip} ra,dec,z FROM SpecObj "
            f"WHERE z BETWEEN {z_lo} AND {z_hi} "
            f"AND ra BETWEEN {ra0:.4f} AND {ra1:.4f}"
        )
        url = (
            "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
            f"?format=json&cmd={urllib.parse.quote(cmd)}"
        )
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        for table in payload:
            if not isinstance(table, dict):
                continue
            if str(table.get("TableName", "")).lower() in {"sqlquery", "query"}:
                continue
            for r in table.get("Rows") or []:
                if isinstance(r, dict) and "ra" in r and "dec" in r:
                    rows.append(
                        {
                            "ra": float(r["ra"]),
                            "dec": float(r["dec"]),
                            "z": float(r.get("z", 0.0)),
                        }
                    )

    seen: set[tuple[float, float]] = set()
    uniq: list[dict[str, float]] = []
    for r in rows:
        key = (round(r["ra"], 4), round(r["dec"], 4))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    if len(uniq) < 200:
        raise RuntimeError(f"SDSS LRG dense fetch too small ({len(uniq)} rows)")

    envelope = [
        {"TableName": "Table1", "Rows": uniq},
        {
            "TableName": "SqlQuery",
            "Rows": [
                {
                    "query": (
                        f"LRG-dense RA strips n_strips={n_strips} "
                        f"n_per_strip={n_per_strip} z=[{z_lo},{z_hi}] n={len(uniq)}"
                    )
                }
            ],
        },
    ]
    dest.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    cache.record(
        PRODUCT_ID,
        dest,
        url="https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch",
    )
    return dest


def load_lrg_dense_galactic(cache: DataCache | None = None) -> dict[str, Any]:
    """PSCz ∪ sdss_lrg_dense (fetch if missing) as Galactic unit vectors."""
    from polomni.observatory.pipeline.sources.cross_sky import load_galaxy_vectors
    from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog

    cache = cache or DataCache()
    try:
        fetch_sdss_lrg_dense(cache=cache, force=False)
    except Exception as exc:
        fetch_err = str(exc)
    else:
        fetch_err = None

    cat = load_pscz_catalog()
    parts = [equatorial_to_galactic(cat["vecs_eq"])]
    sources = ["iras_pscz"]
    n_lrg = 0
    path = cache.resolved_path(PRODUCT_ID)
    if path is None:
        cand = cache.root / PRODUCT_ID / f"{PRODUCT_ID}.json"
        path = cand if cand.is_file() else None
    if path is not None:
        try:
            eq = load_galaxy_vectors(path)
            parts.append(equatorial_to_galactic(eq))
            sources.append(PRODUCT_ID)
            n_lrg = int(eq.shape[0])
        except Exception as exc:
            fetch_err = fetch_err or str(exc)

    from polomni.observatory.pipeline.sources.dense_tracer import _unique_unit_vectors

    stacked = _unique_unit_vectors(np.vstack(parts))
    return {
        "vecs_gal": stacked,
        "n_galaxies": int(stacked.shape[0]),
        "n_pscz": int(cat["vecs_eq"].shape[0]),
        "n_lrg": n_lrg,
        "sources": sources,
        "fetch_error": fetch_err,
    }


def dense_fisher_report(
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    nside_dir: int = 8,
    n_null: int = 12,
    seed: int = 0,
    cache: DataCache | None = None,
    refresh_lrg: bool = False,
) -> dict[str, Any]:
    """Phase H: Fisher bubble scan on Planck × denser (PSCz∪LRG) tracer."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        high_pass_cmb_map,
        load_rble_scar_axis,
    )

    cache = cache or DataCache()
    if refresh_lrg:
        try:
            fetch_sdss_lrg_dense(cache=cache, force=True)
        except Exception:
            pass

    dense = load_lrg_dense_galactic(cache=cache)
    # Baseline PSCz-only for √N scaling check
    pscz_only = load_dense_tracer_galactic(cache=cache, include_sdss=False)

    mask = galactic_edge_mask(nside, b_cut=b_cut)
    cmb, pid = load_planck_for_search(
        map_product_id="planck_smica_cmb", nside=nside, cache=cache
    )
    cmb_hp = high_pass_cmb_map(cmb, lmin=lmin, mask=mask)
    scar = load_rble_scar_axis()

    delta_dense = galaxy_overdensity_map(dense["vecs_gal"], nside, mask)
    delta_pscz = galaxy_overdensity_map(pscz_only["vecs_gal"], nside, mask)

    fisher_dense = fisher_scan_report(
        cmb_hp,
        delta_dense,
        mask,
        nside_dir=nside_dir,
        n_null=n_null,
        seed=seed,
        scar_axis=scar,
    )
    fisher_pscz = fisher_scan_report(
        cmb_hp,
        delta_pscz,
        mask,
        nside_dir=max(4, nside_dir // 2),
        n_null=max(4, n_null // 2),
        seed=seed + 1,
        scar_axis=scar,
    )

    snr_d = float((fisher_dense.get("observed") or {}).get("fisher_snr", 0.0))
    snr_p = float((fisher_pscz.get("observed") or {}).get("fisher_snr", 0.0))
    n_d = int(dense["n_galaxies"])
    n_p = int(pscz_only["n_galaxies"])
    expected_ratio = float(np.sqrt(n_d / max(n_p, 1)))
    observed_ratio = snr_d / max(abs(snr_p), 1e-6)
    f_sky = float(np.mean(mask))
    forecast = forecast_fisher_snr(snr_d, n_gal_now=n_d, f_sky_now=f_sky)

    p_d = float((fisher_dense.get("null") or {}).get("p_value", 1.0))
    gate = bool(fisher_dense.get("gate_pass"))

    return {
        "phase": "H_dense_lrg_fisher",
        "map_product_id": pid,
        "tracer_dense": {
            "n_galaxies": n_d,
            "n_pscz": dense["n_pscz"],
            "n_lrg": dense["n_lrg"],
            "sources": dense["sources"],
            "fetch_error": dense.get("fetch_error"),
        },
        "tracer_pscz_baseline": {"n_galaxies": n_p},
        "fisher_dense": fisher_dense,
        "fisher_pscz_baseline": {
            "fisher_snr": round(snr_p, 4),
            "p_value": (fisher_pscz.get("null") or {}).get("p_value"),
        },
        "scaling": {
            "snr_dense": round(snr_d, 4),
            "snr_pscz": round(snr_p, 4),
            "n_ratio": round(n_d / max(n_p, 1), 4),
            "expected_snr_ratio_sqrt_n": round(expected_ratio, 4),
            "observed_snr_ratio": round(observed_ratio, 4),
        },
        "forecast_desi_lrg_class": forecast,
        "gate_pass": gate,
        "interpretation": (
            "Dense-tracer Fisher gate PASS — candidate bubble_visible with holdout confirm"
            if gate
            else (
                f"Dense LRG Fisher SNR={snr_d:.2f} (p={p_d:.3f}); "
                f"√N scale check obs/exp={observed_ratio:.2f}/{expected_ratio:.2f}; "
                f"DESI forecast SNR={forecast['snr_forecast']:.1f}. "
                "Visibility still null — multiverse not ruled out."
            )
        ),
    }
