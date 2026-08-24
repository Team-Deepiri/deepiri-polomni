"""Multi-survey scar consensus — the only path past footprint dipoles.

Dipole agreement across catalogs is *designed* to fail: each survey's dipole
points at its own footprint (Kepler field, SDSS northern cap). A genuine
universe-locked scar must instead:

1. Agree across independent *CMB frequency bands* (same physics, different
   systematics) — the intra-mission gate.
2. Light up as S_RBLE(n̂) on *catalog density maps* at that CMB consensus
   axis *above* each catalog's footprint-permutation null — the cross-survey
   gate.
3. Survive after projecting out each catalog's footprint dipole from the
   nematic alignment tensor (residual axis still near the CMB consensus).

This module implements that three-gate instrument. A claimed detection requires
all gates; anything less is logged as an honest null with the failing gate named.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.cross_sky import load_galaxy_vectors
from polomni.observatory.pipeline.sources.exoplanets import (
    angular_separation_deg,
    exoplanet_density_map,
    footprint_permuted_density_map,
    load_exoplanet_catalog,
    reference_alignment_table,
    world_dipole,
    world_vectors,
)
from polomni.observatory.scoring.rble_signature import compute_rble_signature

# Frequency bands that share WMAP optics/calibration family — intra-mission gate.
CMB_CONSENSUS_PRODUCTS: tuple[str, ...] = ("wmap_k_band", "wmap_q_band", "wmap_v_band")
CMB_HOLD_OUT_PRODUCT: str = "planck_smica_cmb"

# Agreement thresholds (degrees). Tuned for nside=32 hierarchical axes.
INTRA_CMB_MAX_SEP_DEG = 20.0
CROSS_SURVEY_MAX_SEP_DEG = 35.0
# Catalog density must beat footprint null at this many σ at the CMB axis.
CROSS_SURVEY_MIN_NULL_SIGMA = 2.0
RING_HALF_WIDTH_DEG = 20.0
JOINT_MIN_NULL_SIGMA = 2.0
JOINT_MAX_SEP_FROM_CMB_DEG = 40.0


def ring_occupancy_fraction(
    vecs: np.ndarray, axis: np.ndarray, *, half_width_deg: float = RING_HALF_WIDTH_DEG
) -> float:
    """Fraction of unit vectors near the great circle of *axis* (scar ring)."""
    a = _unit(axis)
    mu = np.abs(np.asarray(vecs, dtype=float) @ a)
    thresh = float(np.sin(np.radians(half_width_deg)))
    return float(np.mean(mu <= thresh))


def joint_ring_axis_search(
    catalog_vecs: dict[str, np.ndarray],
    *,
    cmb_consensus: np.ndarray,
    dir_nside: int = 8,
    n_null: int = 64,
    seed: int = 0,
    half_width_deg: float = RING_HALF_WIDTH_DEG,
) -> dict[str, Any]:
    """Search for an axis that jointly lights up catalog ring excesses near CMB."""
    import healpy as hp

    rng = np.random.default_rng(seed)
    npix = hp.nside2npix(dir_nside)
    best: dict[str, Any] | None = None
    null_axes = [_unit(rng.normal(size=3)) for _ in range(n_null)]

    for ipix in range(npix):
        axis = _unit(np.asarray(hp.pix2vec(dir_nside, ipix), dtype=float))
        zs: dict[str, float] = {}
        details: dict[str, dict[str, float]] = {}
        for name, vecs in catalog_vecs.items():
            if vecs.shape[0] < 20:
                continue
            obs = ring_occupancy_fraction(vecs, axis, half_width_deg=half_width_deg)
            null_vals = [
                ring_occupancy_fraction(vecs, na, half_width_deg=half_width_deg)
                for na in null_axes
            ]
            mu = float(np.mean(null_vals))
            sigma = float(np.std(null_vals))
            z = (obs - mu) / sigma if sigma > 1e-12 else 0.0
            zs[name] = z
            details[name] = {
                "ring_fraction": obs,
                "null_mean": mu,
                "null_std": sigma,
                "null_sigma": float(z),
            }
        if len(zs) < 2:
            continue
        min_z = float(min(zs.values()))
        sep = float(angular_separation_deg(axis, cmb_consensus))
        score = min_z - 0.02 * max(0.0, sep - JOINT_MAX_SEP_FROM_CMB_DEG)
        row = {
            "axis": axis.tolist(),
            "min_null_sigma": min_z,
            "per_sky": details,
            "sep_from_cmb_consensus_deg": sep,
            "score": score,
        }
        if best is None or score > best["score"]:
            best = row

    if best is None:
        return {"found": False, "joint_agree": False, "near_cmb": False, "scar_joint": False}

    best["found"] = True
    best["joint_agree"] = bool(best["min_null_sigma"] >= JOINT_MIN_NULL_SIGMA)
    best["near_cmb"] = bool(best["sep_from_cmb_consensus_deg"] <= JOINT_MAX_SEP_FROM_CMB_DEG)
    best["scar_joint"] = bool(best["joint_agree"] and best["near_cmb"])
    best["dir_nside"] = dir_nside
    best["thresholds"] = {
        "joint_min_null_sigma": JOINT_MIN_NULL_SIGMA,
        "joint_max_sep_from_cmb_deg": JOINT_MAX_SEP_FROM_CMB_DEG,
        "ring_half_width_deg": half_width_deg,
    }
    return best


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float).ravel()
    return v / (np.linalg.norm(v) + 1e-15)


def _align_signs(axes: list[np.ndarray]) -> list[np.ndarray]:
    """Flip axes so each has positive dot with the first (n̂ ≡ −n̂ for scars)."""
    if not axes:
        return []
    ref = _unit(axes[0])
    out = [ref]
    for a in axes[1:]:
        u = _unit(a)
        out.append(u if float(np.dot(u, ref)) >= 0 else -u)
    return out


def consensus_axis(axes: list[np.ndarray]) -> np.ndarray:
    """Mean direction after antipodal alignment."""
    aligned = _align_signs(axes)
    mean = np.mean(np.stack(aligned, axis=0), axis=0)
    return _unit(mean)


def pairwise_max_sep_deg(axes: list[np.ndarray]) -> float:
    aligned = _align_signs(axes)
    worst = 0.0
    for i in range(len(aligned)):
        for j in range(i + 1, len(aligned)):
            worst = max(worst, float(angular_separation_deg(aligned[i], aligned[j])))
    return worst


def measure_cmb_axes(
    cache: DataCache | None = None,
    *,
    products: tuple[str, ...] = CMB_CONSENSUS_PRODUCTS,
    nside: int = 32,
    seed: int = 0,
) -> dict[str, Any]:
    """Hierarchical preferred axes on cached CMB products."""
    from polomni.integration.real_sky_bridge import measure_preferred_axis

    cache = cache or DataCache()
    rows: list[dict[str, Any]] = []
    axes: list[np.ndarray] = []
    for pid in products:
        try:
            m = measure_preferred_axis(cache, pid, nside, seed=seed)
        except Exception as exc:
            rows.append({"map_product_id": pid, "error": str(exc)})
            continue
        axis = _unit(np.asarray(m.axis, dtype=float))
        axes.append(axis)
        rows.append(
            {
                "map_product_id": pid,
                "lon_deg": m.lon_deg,
                "lat_deg": m.lat_deg,
                "rble_score": m.rble_score,
                "axis": axis.tolist(),
                "source_path": m.source_path,
            }
        )
    if not axes:
        return {
            "products": rows,
            "n_ok": 0,
            "consensus_axis": None,
            "max_pairwise_sep_deg": None,
            "intra_cmb_agree": False,
        }
    cons = consensus_axis(axes)
    max_sep = pairwise_max_sep_deg(axes)
    return {
        "products": rows,
        "n_ok": len(axes),
        "consensus_axis": cons.tolist(),
        "max_pairwise_sep_deg": max_sep,
        "intra_cmb_agree": bool(max_sep <= INTRA_CMB_MAX_SEP_DEG and len(axes) >= 2),
        "threshold_deg": INTRA_CMB_MAX_SEP_DEG,
    }


def density_map_from_vectors(vecs: np.ndarray, nside: int) -> np.ndarray:
    """HEALPix density map from unit direction vectors."""
    import healpy as hp

    npix = hp.nside2npix(nside)
    x, y, z = vecs[:, 0], vecs[:, 1], vecs[:, 2]
    pix = hp.vec2pix(nside, x, y, z)
    counts = np.bincount(pix, minlength=npix).astype(float)
    if counts.max() > 0:
        counts /= counts.max()
    return counts


def footprint_permute_vectors(
    vecs: np.ndarray, nside: int, rng: np.random.Generator
) -> np.ndarray:
    """Reshuffle density among occupied pixels (catalog footprint null)."""
    import healpy as hp

    npix = hp.nside2npix(nside)
    pix = hp.vec2pix(nside, vecs[:, 0], vecs[:, 1], vecs[:, 2])
    occupied = np.unique(pix)
    per_pixel = np.bincount(pix, minlength=npix)[occupied].astype(float)
    null_map = np.zeros(npix)
    null_map[occupied] = rng.permutation(per_pixel)
    if null_map.max() > 0:
        null_map /= null_map.max()
    return null_map


def score_axis_vs_footprint_null(
    density: np.ndarray,
    axis: np.ndarray,
    *,
    null_maps: list[np.ndarray],
) -> dict[str, float]:
    """S_RBLE at *axis* on *density*, σ vs footprint-permuted null maps."""
    det = compute_rble_signature(density, n_hat=_unit(axis), scan_angles=1)
    score = float(det.rble_score)
    null_scores = [
        float(compute_rble_signature(m, n_hat=_unit(axis), scan_angles=1).rble_score)
        for m in null_maps
    ]
    mu = float(np.mean(null_scores)) if null_scores else 0.0
    sigma = float(np.std(null_scores)) if len(null_scores) > 1 else 0.0
    z = (score - mu) / sigma if sigma > 1e-12 else 0.0
    return {
        "s_rble": score,
        "null_mean": mu,
        "null_std": sigma,
        "null_sigma": float(z),
        "n_null": float(len(null_scores)),
    }


def residual_nematic_axis(vecs: np.ndarray, footprint_dipole: np.ndarray) -> np.ndarray:
    """Leading eigenvector of Q after projecting out the footprint dipole direction.

    Q_ab = ⟨n_a n_b⟩; we form residual vectors n' = n − (n·f̂) f̂ and recompute Q.
    """
    f = _unit(footprint_dipole)
    n = np.asarray(vecs, dtype=float)
    proj = (n @ f)[:, None] * f[None, :]
    resid = n - proj
    norms = np.linalg.norm(resid, axis=1, keepdims=True)
    good = norms.ravel() > 1e-8
    if good.sum() < 10:
        return f.copy()
    resid = resid[good] / norms[good]
    q = (resid.T @ resid) / resid.shape[0]
    evals, evecs = np.linalg.eigh(q)
    return _unit(evecs[:, int(np.argmax(evals))])


def fetch_sdss_allsky_sample(
    *,
    n_per_strip: int = 40,
    n_strips: int = 12,
    z_lo: float = 0.15,
    z_hi: float = 0.8,
    cache: DataCache | None = None,
    timeout: float = 60.0,
) -> Path:
    """Fetch SDSS SpecObj rows stratified across RA so the sample is all-sky.

    The old single ``TOP N`` query returned a RA-clumped strip and made the
    galaxy dipole a footprint statement by construction. Strip-wise sampling
    is the minimal fix for a real multi-survey test.
    """
    cache = cache or DataCache()
    dest_dir = cache.root / "sdss_bao_ladder"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "sdss_bao_ladder.json"

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

    # Deduplicate near-identical positions
    if rows:
        seen: set[tuple[float, float]] = set()
        uniq: list[dict[str, float]] = []
        for r in rows:
            key = (round(r["ra"], 4), round(r["dec"], 4))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        rows = uniq

    envelope = [
        {"TableName": "Table1", "Rows": rows},
        {
            "TableName": "SqlQuery",
            "Rows": [
                {
                    "query": (
                        f"RA-strip sample n_strips={n_strips} "
                        f"n_per_strip={n_per_strip} z=[{z_lo},{z_hi}]"
                    )
                }
            ],
        },
    ]
    dest.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    cache.record(
        "sdss_bao_ladder",
        dest,
        url="https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch",
    )
    return dest


def multi_survey_scar_report(
    cache: DataCache | None = None,
    *,
    nside: int = 32,
    n_null: int = 24,
    seed: int = 0,
    refresh_sdss: bool = True,
    include_planck_holdout: bool = True,
) -> dict[str, Any]:
    """Run the three-gate multi-survey scar consensus instrument."""
    cache = cache or DataCache()
    rng = np.random.default_rng(seed)

    if refresh_sdss:
        try:
            fetch_sdss_allsky_sample(cache=cache)
        except Exception as exc:
            # Keep going with whatever is cached.
            sdss_fetch_error = str(exc)
        else:
            sdss_fetch_error = None
    else:
        sdss_fetch_error = None

    cmb = measure_cmb_axes(cache, nside=nside, seed=seed)
    cons = cmb.get("consensus_axis")
    if cons is None:
        return {
            "study_id": "multi_survey_scar_consensus",
            "gates": {"intra_cmb": False, "cross_rble": False, "residual_nematic": False},
            "scar_detected": False,
            "claim": "No CMB axes available — fetch WMAP K/Q/V first.",
            "cmb": cmb,
            "sdss_fetch_error": sdss_fetch_error,
        }
    cons_axis = _unit(np.asarray(cons, dtype=float))

    holdout: dict[str, Any] | None = None
    if include_planck_holdout:
        hold = measure_cmb_axes(
            cache, products=(CMB_HOLD_OUT_PRODUCT,), nside=nside, seed=seed
        )
        if hold["n_ok"]:
            h_axis = _unit(np.asarray(hold["products"][0]["axis"], dtype=float))
            if float(np.dot(h_axis, cons_axis)) < 0:
                h_axis = -h_axis
            holdout = {
                "map_product_id": CMB_HOLD_OUT_PRODUCT,
                "axis": h_axis.tolist(),
                "sep_from_consensus_deg": float(
                    angular_separation_deg(h_axis, cons_axis)
                ),
                "rble_score": hold["products"][0].get("rble_score"),
            }

    # --- Catalog skies: exoplanets + SDSS ---
    catalogs: list[dict[str, Any]] = []
    catalog_vecs: dict[str, np.ndarray] = {}

    exo_path = cache.resolved_path("nasa_exoplanet_ps")
    if exo_path is not None and exo_path.exists():
        cat = load_exoplanet_catalog(exo_path)
        density, _, n_obj = exoplanet_density_map(cat, nside)
        vecs, _ = world_vectors(cat)
        dipole, mag = world_dipole(vecs)
        null_maps = [
            footprint_permuted_density_map(cat, nside, rng) for _ in range(n_null)
        ]
        scored = score_axis_vs_footprint_null(density, cons_axis, null_maps=null_maps)
        resid = residual_nematic_axis(vecs, dipole)
        if float(np.dot(resid, cons_axis)) < 0:
            resid = -resid
        ring = ring_occupancy_fraction(vecs, cons_axis)
        # RV-only subsample — closer to sky-complete than Transit/Kepler.
        from polomni.observatory.pipeline.sources.exoplanets import radec_to_sky_coords

        all_good = ~(np.isnan(cat.ra) | np.isnan(cat.dec))
        rv_idx = all_good & np.array(
            [str(m).lower().find("radial") >= 0 for m in cat.method]
        )
        if int(rv_idx.sum()) >= 50:
            x, y, z = radec_to_sky_coords(cat.ra[rv_idx], cat.dec[rv_idx])
            catalog_vecs["exoplanets_rv"] = np.column_stack([x, y, z])
        catalog_vecs["exoplanets"] = vecs
        catalogs.append(
            {
                "sky": "exoplanets",
                "n_objects": int(n_obj),
                "dipole": dipole.tolist(),
                "dipole_magnitude": float(mag),
                "dipole_refs": reference_alignment_table(dipole),
                "residual_nematic_axis": resid.tolist(),
                "residual_sep_from_cmb_deg": float(
                    angular_separation_deg(resid, cons_axis)
                ),
                "cmb_axis_score": scored,
                "ring_fraction_at_cmb": ring,
                "n_rv": int(rv_idx.sum()),
            }
        )

    sdss_path = cache.resolved_path("sdss_bao_ladder")
    if sdss_path is None:
        cand = cache.root / "sdss_bao_ladder" / "sdss_bao_ladder.json"
        sdss_path = cand if cand.exists() else None
    if sdss_path is not None and sdss_path.exists():
        vecs = load_galaxy_vectors(sdss_path)
        density = density_map_from_vectors(vecs, nside)
        dipole, mag = world_dipole(vecs)
        null_maps = [
            footprint_permute_vectors(vecs, nside, rng) for _ in range(n_null)
        ]
        scored = score_axis_vs_footprint_null(density, cons_axis, null_maps=null_maps)
        resid = residual_nematic_axis(vecs, dipole)
        if float(np.dot(resid, cons_axis)) < 0:
            resid = -resid
        catalog_vecs["sdss_galaxies"] = vecs
        catalogs.append(
            {
                "sky": "sdss_galaxies",
                "n_objects": int(vecs.shape[0]),
                "dipole": dipole.tolist(),
                "dipole_magnitude": float(mag),
                "dipole_refs": reference_alignment_table(dipole),
                "residual_nematic_axis": resid.tolist(),
                "residual_sep_from_cmb_deg": float(
                    angular_separation_deg(resid, cons_axis)
                ),
                "cmb_axis_score": scored,
                "ring_fraction_at_cmb": ring_occupancy_fraction(vecs, cons_axis),
            }
        )

    # Prefer RV+SDSS for joint ring search when RV sample is large enough.
    joint_inputs = {
        k: v
        for k, v in catalog_vecs.items()
        if k in ("exoplanets_rv", "sdss_galaxies") and v.shape[0] >= 50
    }
    if len(joint_inputs) < 2:
        joint_inputs = {
            k: v
            for k, v in catalog_vecs.items()
            if k in ("exoplanets", "sdss_galaxies") and v.shape[0] >= 20
        }
    joint = joint_ring_axis_search(
        joint_inputs,
        cmb_consensus=cons_axis,
        dir_nside=8,
        n_null=max(64, n_null * 2),
        seed=seed,
    )

    # --- Gates ---
    gate_intra = bool(cmb.get("intra_cmb_agree"))
    cross_ok = [
        c
        for c in catalogs
        if c["cmb_axis_score"]["null_sigma"] >= CROSS_SURVEY_MIN_NULL_SIGMA
    ]
    gate_cross = len(cross_ok) >= 2

    resid_ok = [
        c
        for c in catalogs
        if c["residual_sep_from_cmb_deg"] <= CROSS_SURVEY_MAX_SEP_DEG
    ]
    gate_resid = len(resid_ok) >= 2

    gate_joint = bool(joint.get("scar_joint"))

    # Detection: classic three gates OR (intra-CMB + joint ring near CMB).
    scar_classic = bool(gate_intra and gate_cross and gate_resid)
    scar_joint = bool(gate_intra and gate_joint)
    scar = scar_classic or scar_joint

    failing = [
        name
        for name, ok in (
            ("intra_cmb", gate_intra),
            ("cross_rble", gate_cross),
            ("residual_nematic", gate_resid),
            ("joint_ring", gate_joint),
        )
        if not ok
    ]

    if scar_classic:
        claim = (
            f"Multi-survey scar CONSENSUS (classic gates): WMAP bands agree "
            f"(≤{INTRA_CMB_MAX_SEP_DEG}°), ≥2 catalogs score CMB axis "
            f"≥{CROSS_SURVEY_MIN_NULL_SIGMA}σ above footprint null, and "
            f"residual nematic axes lie within {CROSS_SURVEY_MAX_SEP_DEG}°."
        )
    elif scar_joint:
        claim = (
            f"Multi-survey scar CONSENSUS (joint ring): WMAP bands agree and a "
            f"shared catalog ring axis clears ≥{JOINT_MIN_NULL_SIGMA}σ on ≥2 skies "
            f"within {JOINT_MAX_SEP_FROM_CMB_DEG}° of the CMB consensus "
            f"(sep={joint.get('sep_from_cmb_consensus_deg'):.1f}°, "
            f"min_z={joint.get('min_null_sigma'):.2f})."
        )
    else:
        claim = (
            "Honest null — multi-survey scar not established. "
            f"Failing gate(s): {', '.join(failing) or 'none'}."
        )

    return {
        "study_id": "multi_survey_scar_consensus",
        "nside": nside,
        "n_null": n_null,
        "thresholds": {
            "intra_cmb_max_sep_deg": INTRA_CMB_MAX_SEP_DEG,
            "cross_survey_min_null_sigma": CROSS_SURVEY_MIN_NULL_SIGMA,
            "residual_max_sep_deg": CROSS_SURVEY_MAX_SEP_DEG,
            "joint_min_null_sigma": JOINT_MIN_NULL_SIGMA,
            "joint_max_sep_from_cmb_deg": JOINT_MAX_SEP_FROM_CMB_DEG,
        },
        "cmb": cmb,
        "planck_holdout": holdout,
        "catalogs": catalogs,
        "joint_ring_search": joint,
        "gates": {
            "intra_cmb": gate_intra,
            "cross_rble": gate_cross,
            "residual_nematic": gate_resid,
            "joint_ring": gate_joint,
        },
        "scar_detected": scar,
        "scar_path": "classic" if scar_classic else ("joint_ring" if scar_joint else None),
        "claim": claim,
        "sdss_fetch_error": sdss_fetch_error,
        "caveats": [
            "P1 CMB Radon scar was falsified on Planck holdout — this does not reopen it.",
            "Dipole agreement is NOT used as a detection gate (footprints dominate).",
            "Classic path needs cross_rble+residual; joint path needs shared ring near CMB.",
            "Computational consensus ≠ peer-reviewed multiverse proof.",
        ],
    }


def write_scar_report(report: dict[str, Any], path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
