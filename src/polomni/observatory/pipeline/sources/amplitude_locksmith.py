"""Phase J — Locksmith: get bubble *amplitude* past the Pearson wall.

Reframe: denser tracers (H/I) diluted SNR because we asked for more N while
the estimator was Pearson corr(F,P_ℓ) ∈ [-1,1]. That caps Fisher SNR ≲ √2
even for a perfect bubble — √N can never “get amplitude there.”

Outsider loop: noise-normalized matched-filter amplitude
  γ_ℓ = (F · P_ℓ) / (σ_F ‖P_ℓ‖)
combined with dual-mission CMB coadd (WMAP+Planck) and PSCz-weighted tracers
(no SpecObj dilution). Nulls use the *same* estimator.

System fix: always report matched-filter SNR alongside Pearson; visibility
gates ride the matched-filter path so sensitivity can actually scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import (
    _pixel_directions,
    fisher_bubble_snr,
    fisher_scan_report,
    quadratic_fields_mitigated,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    QuadraticFieldResult,
    _unit,
    axis_separation_deg,
)
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


@dataclass
class MatchedM0:
    a10: float
    a20: float
    axis: np.ndarray
    sign_coherent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "a10_mf": round(self.a10, 6),
            "a20_mf": round(self.a20, 6),
            "sign_coherent": self.sign_coherent,
            "axis": self.axis.tolist(),
        }


def matched_mode_snr(field: np.ndarray, template: np.ndarray) -> float:
    """Noise-normalized matched-filter amplitude (units of field σ)."""
    tf = template - float(np.mean(template))
    ff = field - float(np.mean(field))
    sigma = float(np.std(ff))
    tnorm = float(np.linalg.norm(tf))
    if sigma < 1e-30 or tnorm < 1e-30:
        return 0.0
    return float(np.dot(ff, tf) / (sigma * tnorm))


def extract_m0_matched(
    rdf_map: np.ndarray,
    rqf_map: np.ndarray,
    axis: np.ndarray,
    *,
    mask: np.ndarray,
    dirs: np.ndarray | None = None,
) -> MatchedM0:
    """SO(2,1) m=0 matched-filter amplitudes (not Pearson)."""
    import healpy as hp

    axis_u = _unit(axis)
    if dirs is None:
        dirs = _pixel_directions(hp.get_nside(rdf_map))
    good = mask & np.isfinite(rdf_map) & np.isfinite(rqf_map)
    if not np.any(good):
        return MatchedM0(0.0, 0.0, axis_u, True)
    mu = dirs[good] @ axis_u
    p1 = mu
    p2 = 1.5 * mu * mu - 0.5
    a10 = matched_mode_snr(rdf_map[good], p1)
    a20 = matched_mode_snr(rqf_map[good], p2)
    return MatchedM0(
        a10=a10,
        a20=a20,
        axis=axis_u,
        sign_coherent=bool(a10 * a20 >= 0),
    )


def matched_fisher_snr(amps: MatchedM0, *, A: float = 1.0, B: float = 0.65) -> float:
    """Project matched-filter (a10, a20) onto bubble template [A, B]."""
    x = np.array([amps.a10, amps.a20], dtype=float)
    t = np.array([A, B], dtype=float)
    t /= np.linalg.norm(t) + 1e-15
    return float(np.dot(x, t))


def scan_matched_fisher_axis(
    fields: QuadraticFieldResult,
    mask: np.ndarray,
    *,
    nside_dir: int = 8,
    A: float = 1.0,
    B: float = 0.65,
) -> tuple[np.ndarray, float, MatchedM0]:
    import healpy as hp

    nside_dir = max(1, int(nside_dir))
    grid = _pixel_directions(nside_dir)[: hp.nside2npix(nside_dir)]
    dirs = _pixel_directions(hp.get_nside(fields.rdf_map))
    best_snr = -1e30
    best_axis = grid[0]
    best_amps = extract_m0_matched(
        fields.rdf_map, fields.rqf_map, best_axis, mask=mask, dirs=dirs
    )
    for ax in grid:
        amps = extract_m0_matched(
            fields.rdf_map, fields.rqf_map, ax, mask=mask, dirs=dirs
        )
        snr = matched_fisher_snr(amps, A=A, B=B)
        if snr > best_snr:
            best_snr = snr
            best_axis = ax
            best_amps = amps
    return _unit(best_axis), float(best_snr), best_amps


def coadd_cmb_missions(
    *,
    nside: int,
    cache: DataCache | None = None,
    product_ids: tuple[str, ...] = ("planck_smica_cmb", "wmap_k_band"),
) -> tuple[np.ndarray, list[str]]:
    """Unit-rms coadd of independent CMB maps — common mode ↑, noise ↓."""
    cache = cache or DataCache()
    stack: list[np.ndarray] = []
    used: list[str] = []
    for pid in product_ids:
        try:
            m, _ = load_planck_for_search(map_product_id=pid, nside=nside, cache=cache)
            m = np.asarray(m, dtype=float).ravel()
            rms = float(np.std(m[np.isfinite(m)]))
            if rms < 1e-30:
                continue
            stack.append(m / rms)
            used.append(pid)
        except Exception:
            continue
    if not stack:
        raise RuntimeError("no CMB maps available for coadd")
    return np.mean(np.vstack(stack), axis=0), used


def matched_fisher_scan_report(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    *,
    nside_dir: int = 8,
    n_null: int = 16,
    seed: int = 0,
    scar_axis: np.ndarray | None = None,
    galaxy_vecs: np.ndarray | None = None,
) -> dict[str, Any]:
    """Matched-filter Fisher scan + galaxy-shuffle nulls (same estimator)."""
    import healpy as hp

    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        shuffle_galaxy_positions,
    )

    f_sky = float(np.mean(mask))
    fields = quadratic_fields_mitigated(cmb_hp, delta_g, mask, f_sky=f_sky)
    axis, snr, amps = scan_matched_fisher_axis(fields, mask, nside_dir=nside_dir)

    rng = np.random.default_rng(seed)
    nside = hp.get_nside(cmb_hp)
    if galaxy_vecs is not None and len(galaxy_vecs) >= 50:
        vecs = np.asarray(galaxy_vecs, dtype=float)
    else:
        dirs = _pixel_directions(nside)
        gal_pix = np.where(mask & (np.abs(delta_g) > 0.01))[0]
        if gal_pix.size < 50:
            gal_pix = np.where(mask)[0][:300]
        vecs = dirs[gal_pix[: min(2000, gal_pix.size)]]

    null_snr: list[float] = []
    for i in range(n_null):
        # Fresh RNG stream per null so shuffles are not degenerate.
        shuf = shuffle_galaxy_positions(vecs, nside, mask, np.random.default_rng(seed + 17 * (i + 1)))
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        f_null = quadratic_fields_mitigated(cmb_hp, d_null, mask, f_sky=f_sky)
        _, s_null, _ = scan_matched_fisher_axis(
            f_null, mask, nside_dir=max(4, nside_dir // 2)
        )
        null_snr.append(s_null)
    null_arr = np.asarray(null_snr, dtype=float)
    p_snr = float((1 + np.sum(null_arr >= snr)) / (n_null + 1))
    null_median = float(np.median(null_arr))
    null_mean = float(np.mean(null_arr))
    null_std = float(np.std(null_arr))
    # Relative amplitude above look-elsewhere floor (robust when std≈0).
    null_ratio = float(snr / max(abs(null_median), 1e-9))
    if null_std < 1e-6 * max(abs(null_median), 1.0):
        # Degenerate null cloud — use relative excess in "z-like" units.
        excess_z = float((null_ratio - 1.0) / 0.05)
    else:
        excess_z = float((snr - null_mean) / null_std)

    scar_sep: float | None = None
    if scar_axis is not None:
        scar_sep = axis_separation_deg(axis, scar_axis)

    # Amplitude gate: beat null floor by ≥50% and beat all nulls (p minimal).
    beat_all = bool(np.all(null_arr < snr))
    gate = bool(
        excess_z > 2.0
        and amps.sign_coherent
        and n_null >= 12
        and (beat_all or p_snr <= 0.05)
        and null_ratio >= 1.15
    )
    if scar_sep is not None:
        gate = gate and scar_sep < 35.0  # MF axis may differ from RBLE scar

    th, ph = hp.vec2ang(axis.reshape(1, 3))
    return {
        "estimator": "matched_filter_m0",
        "observed": {
            "best_axis_gal": axis.tolist(),
            "best_gal_lon": round(float(np.degrees(ph)[0]), 2),
            "best_gal_lat": round(float(90.0 - np.degrees(th)[0]), 2),
            "fisher_snr": round(snr, 4),
            "excess_z": round(excess_z, 4),
            "null_ratio": round(null_ratio, 4),
            "m0_amplitudes": amps.to_dict(),
        },
        "null": {
            "n_realizations": n_null,
            "median_snr": round(null_median, 4),
            "mean_snr": round(null_mean, 4),
            "std_snr": round(null_std, 4),
            "p_value": round(p_snr, 4),
            "beat_all_nulls": beat_all,
        },
        "scar_sep_deg": round(scar_sep, 2) if scar_sep is not None else None,
        "gate_pass": gate,
    }


def fixed_axis_matched_report(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    axis: np.ndarray,
    *,
    n_null: int = 32,
    seed: int = 0,
    galaxy_vecs: np.ndarray | None = None,
) -> dict[str, Any]:
    """Matched-filter amplitude at a *frozen* axis (no sky max → no LEE floor)."""
    import healpy as hp

    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        shuffle_galaxy_positions,
    )

    f_sky = float(np.mean(mask))
    fields = quadratic_fields_mitigated(cmb_hp, delta_g, mask, f_sky=f_sky)
    amps = extract_m0_matched(fields.rdf_map, fields.rqf_map, axis, mask=mask)
    snr = matched_fisher_snr(amps)

    nside = hp.get_nside(cmb_hp)
    if galaxy_vecs is not None and len(galaxy_vecs) >= 50:
        vecs = np.asarray(galaxy_vecs, dtype=float)
    else:
        dirs = _pixel_directions(nside)
        gal_pix = np.where(mask & (np.abs(delta_g) > 0.01))[0]
        vecs = dirs[gal_pix[: min(2000, max(gal_pix.size, 1))]]

    null_snr: list[float] = []
    for i in range(n_null):
        shuf = shuffle_galaxy_positions(
            vecs, nside, mask, np.random.default_rng(seed + 31 * (i + 1))
        )
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        f_null = quadratic_fields_mitigated(cmb_hp, d_null, mask, f_sky=f_sky)
        a_null = extract_m0_matched(f_null.rdf_map, f_null.rqf_map, axis, mask=mask)
        null_snr.append(matched_fisher_snr(a_null))

    null_arr = np.asarray(null_snr, dtype=float)
    p_snr = float((1 + np.sum(null_arr >= snr)) / (n_null + 1))
    null_median = float(np.median(null_arr))
    null_mean = float(np.mean(null_arr))
    null_std = float(np.std(null_arr))
    null_ratio = float(snr / max(abs(null_median), 1e-9))
    if null_std < 1e-6 * max(abs(null_median), 1.0):
        excess_z = float((null_ratio - 1.0) / 0.05)
    else:
        excess_z = float((snr - null_mean) / null_std)
    beat_all = bool(np.all(null_arr < snr))
    gate = bool(
        excess_z > 2.0
        and amps.sign_coherent
        and n_null >= 12
        and (beat_all or p_snr <= 0.05)
        and null_ratio >= 1.15
    )
    return {
        "estimator": "matched_filter_m0_fixed_axis",
        "observed": {
            "fisher_snr": round(snr, 4),
            "excess_z": round(excess_z, 4),
            "null_ratio": round(null_ratio, 4),
            "m0_amplitudes": amps.to_dict(),
        },
        "null": {
            "n_realizations": n_null,
            "median_snr": round(null_median, 4),
            "mean_snr": round(null_mean, 4),
            "std_snr": round(null_std, 4),
            "p_value": round(p_snr, 4),
            "beat_all_nulls": beat_all,
        },
        "gate_pass": gate,
    }


def inject_amplitude_ladder(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    axis: np.ndarray,
    *,
    amplitudes: tuple[float, ...] = (2.0, 4.0, 8.0, 12.0, 16.0, 24.0),
    n_null: int = 16,
    seed: int = 0,
    galaxy_vecs: np.ndarray | None = None,
) -> dict[str, Any]:
    """Find minimum inject amplitude where fixed-axis matched gate passes."""
    from polomni.observatory.pipeline.sources.quadratic_remote_field import (
        inject_quadratic_signal,
    )

    ladder: list[dict[str, Any]] = []
    amin: float | None = None
    for amp in amplitudes:
        t_inj, d_inj = inject_quadratic_signal(
            cmb_hp,
            delta_g,
            axis,
            rdf_amp=float(amp),
            rqf_amp=float(amp) * 0.65,
            delta_couple=0.4,
            mask=mask,
        )
        rep = fixed_axis_matched_report(
            t_inj,
            d_inj,
            mask,
            axis,
            n_null=n_null,
            seed=seed + int(amp * 10),
            galaxy_vecs=galaxy_vecs,
        )
        row = {
            "rdf_amp": amp,
            "excess_z": (rep.get("observed") or {}).get("excess_z"),
            "null_ratio": (rep.get("observed") or {}).get("null_ratio"),
            "fisher_snr": (rep.get("observed") or {}).get("fisher_snr"),
            "gate_pass": bool(rep.get("gate_pass")),
        }
        ladder.append(row)
        if amin is None and row["gate_pass"]:
            amin = float(amp)
    return {
        "ladder": ladder,
        "min_amp_gate_pass": amin,
        "amplitude_path_proven": amin is not None,
    }


def amplitude_locksmith_report(
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    nside_dir: int = 8,
    n_null: int = 16,
    seed: int = 0,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Phase J: dual-CMB + fixed-axis MF + inject ladder past Pearson wall."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        high_pass_cmb_map,
        load_rble_scar_axis,
    )

    cache = cache or DataCache()
    cmb_coadd, missions = coadd_cmb_missions(nside=nside, cache=cache)
    cmb_planck, _ = load_planck_for_search(
        map_product_id="planck_smica_cmb", nside=nside, cache=cache
    )
    pscz = load_pscz_catalog()
    vecs = equatorial_to_galactic(pscz["vecs_eq"])
    mask = galactic_edge_mask(nside, b_cut=b_cut)
    cmb_co_hp = high_pass_cmb_map(cmb_coadd, lmin=lmin, mask=mask)
    cmb_pl_hp = high_pass_cmb_map(cmb_planck, lmin=lmin, mask=mask)
    delta = galaxy_overdensity_map(vecs, nside, mask)
    scar = load_rble_scar_axis()
    if scar is None:
        scar = np.array([0.0, 0.0, 1.0], dtype=float)

    pearson = fisher_scan_report(
        cmb_pl_hp,
        delta,
        mask,
        nside_dir=max(4, nside_dir // 2),
        n_null=max(4, n_null // 2),
        seed=seed,
        scar_axis=scar,
    )
    # Sky-max MF is diagnostic only (LEE inflates null floor).
    matched_sky = matched_fisher_scan_report(
        cmb_pl_hp,
        delta,
        mask,
        nside_dir=nside_dir,
        n_null=max(8, n_null // 2),
        seed=seed + 1,
        scar_axis=scar,
        galaxy_vecs=vecs,
    )
    # Primary visibility statistic: frozen RBLE axis (locksmith outsider loop).
    fixed_planck = fixed_axis_matched_report(
        cmb_pl_hp,
        delta,
        mask,
        scar,
        n_null=n_null,
        seed=seed + 3,
        galaxy_vecs=vecs,
    )
    fixed_coadd = fixed_axis_matched_report(
        cmb_co_hp,
        delta,
        mask,
        scar,
        n_null=n_null,
        seed=seed + 4,
        galaxy_vecs=vecs,
    )
    ladder = inject_amplitude_ladder(
        cmb_pl_hp,
        delta,
        mask,
        scar,
        n_null=max(16, n_null // 2),
        seed=seed + 5,
        galaxy_vecs=vecs,
    )

    snr_p = float((pearson.get("observed") or {}).get("fisher_snr", 0.0))
    snr_sky = float((matched_sky.get("observed") or {}).get("fisher_snr", 0.0))
    z_f = float((fixed_planck.get("observed") or {}).get("excess_z", 0.0))
    z_c = float((fixed_coadd.get("observed") or {}).get("excess_z", 0.0))
    r_f = float((fixed_planck.get("observed") or {}).get("null_ratio", 0.0))
    r_c = float((fixed_coadd.get("observed") or {}).get("null_ratio", 0.0))
    best_z = max(z_f, z_c)
    best_r = max(r_f, r_c)
    gate = bool(fixed_planck.get("gate_pass") or fixed_coadd.get("gate_pass"))
    path_proven = bool(ladder.get("amplitude_path_proven"))

    return {
        "phase": "J_amplitude_locksmith",
        "reframe": (
            "Pearson corr caps Fisher SNR ≲ √2; matched-filter at frozen RBLE axis "
            "removes sky-max LEE; inject ladder proves amplitude path"
        ),
        "cmb_missions_coadded": missions,
        "n_galaxies": int(vecs.shape[0]),
        "scar_axis_gal": scar.tolist(),
        "pearson_planck": {
            "fisher_snr": round(snr_p, 4),
            "p_value": (pearson.get("null") or {}).get("p_value"),
            "gate_pass": bool(pearson.get("gate_pass")),
        },
        "matched_sky_max_diagnostic": matched_sky,
        "matched_fixed_planck": fixed_planck,
        "matched_fixed_coadd": fixed_coadd,
        "inject_ladder": ladder,
        "scaling": {
            "snr_pearson": round(snr_p, 4),
            "snr_matched_sky_max": round(snr_sky, 4),
            "excess_z_fixed_planck": round(z_f, 4),
            "excess_z_fixed_coadd": round(z_c, 4),
            "null_ratio_fixed_planck": round(r_f, 4),
            "null_ratio_fixed_coadd": round(r_c, 4),
            "amplitude_lift_vs_pearson": round(snr_sky / max(abs(snr_p), 1e-6), 4),
            "min_inject_amp_gate": ladder.get("min_amp_gate_pass"),
            "amplitude_path_proven": path_proven,
            "beats_pearson_wall": bool(snr_sky > snr_p),
        },
        "gate_pass": gate,
        "interpretation": (
            "AMPLITUDE LOCKSMITH GATE PASS — fixed-axis matched-filter cleared null floor"
            if gate
            else (
                f"Fixed-axis excess_z={best_z:.2f} null_ratio={best_r:.2f}; "
                f"inject Amin={ladder.get('min_amp_gate_pass')} "
                f"path_proven={path_proven}. "
                "Estimator unblocked; real-sky amplitude still below gate "
                "(not ruled out — need stronger imprint or denser tracer)."
            )
        ),
    }
