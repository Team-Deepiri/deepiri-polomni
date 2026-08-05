"""Bubble-collision search — the falsifiable multiverse observable.

In eternal inflation, our bubble universe can collide with another bubble of
different vacuum energy. The collision leaves an observable signature on our
past light cone: a roughly **circular temperature edge** in the CMB — a step
in temperature across the boundary of the collided region (Kleban; Aguirre,
Johnson & Larfors; Feeney et al. 2011 "First observational tests of eternal
inflation").

This module builds the search instrument:

* ``circle_edge_statistic`` — mean temperature just outside vs just inside a
  candidate circle boundary (the edge amplitude, in µK).
* ``bubble_scan_geometry`` — precomputes the ring pixel lists for a grid of
  centers × radii (identical for every null realization, so the scan is
  cheap per map).
* ``bubble_collision_report`` — runs the scan on a real CMB map, compares the
  strongest edge against a C_ℓ-matched Gaussian null (with the same sky mask),
  and reports the most significant circular edge on the sky.
* ``inject_bubble_collision`` — plants a synthetic collision step into a map
  so the instrument can be validated by signal recovery.

Honesty contract: the null is C_ℓ-matched (preserves the true large-scale
correlation structure) and mask-matched; the look-elsewhere effect is handled
by asking how often *any* circle in the null exceeds the observed maximum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.ingest.healpix_loader import (
    downsample_map,
    load_healpix_map,
)
from polomni.observatory.pipeline.cache import DataCache

_GEOMETRY_CACHE: dict[tuple[Any, ...], Any] = {}


def galactic_edge_mask(nside: int, b_cut: float = 20.0) -> np.ndarray:
    """Boolean mask (True = kept) excluding the Galactic plane |b| < b_cut.

    The standard f_sky cut for large-angle CMB analysis. The Galactic plane
    is foreground-dominated and would otherwise read as a giant fake edge.

    Planck and WMAP all-sky maps ship in **Galactic** coordinates, so the
    Galactic latitude is read directly from the HEALPix colatitude theta
    (no frame rotation — rotating again would mask the wrong strip).
    """
    import healpy as hp

    npix = hp.nside2npix(nside)
    theta, _ = hp.pix2ang(nside, np.arange(npix))
    good = np.abs(90.0 - np.degrees(theta)) >= b_cut
    return good


@dataclass
class CircleGeometry:
    """Precomputed ring pixel lists for one candidate (center, radius)."""

    center_idx: int
    theta_rad: float
    phi_rad: float
    radius_deg: float
    inner_pix: np.ndarray
    outer_pix: np.ndarray


def _ring_pix(nside: int, vec: np.ndarray, mask: np.ndarray, r1: float, r2: float) -> np.ndarray:
    """Pixel indices with angular distance in [r1, r2) radians, mask-applied."""
    import healpy as hp

    if r1 <= 0.0:
        inside_outer = hp.query_disc(nside, vec, r2, inclusive=True)
        pix = inside_outer
    else:
        inside_inner = hp.query_disc(nside, vec, r1, inclusive=True)
        inside_outer = hp.query_disc(nside, vec, r2, inclusive=True)
        pix = np.setdiff1d(inside_outer, inside_inner, assume_unique=True)
    good = mask[pix]
    return pix[good]


def bubble_scan_geometry(
    nside: int = 128,
    nside_dir: int = 8,
    radii_deg: tuple[float, ...] = (15.0, 25.0, 35.0, 45.0, 55.0, 65.0, 75.0),
    width_deg: float = 5.0,
    b_cut: float = 20.0,
) -> tuple[list[CircleGeometry], np.ndarray]:
    """Precompute ring geometry for a grid of centers × radii.

    Centers are HEALPix pixel centers at ``nside_dir``. For each candidate
    circle we store the pixel lists for the inner ring (radius − w/2 .. radius)
    and outer ring (radius .. radius + w/2), with the Galactic mask already
    applied. Geometry is independent of the map values, so it is cached and
    reused across the observed map and every null realization.

    Returns (geometries, mask).
    """
    key = (nside, nside_dir, radii_deg, width_deg, b_cut)
    if key in _GEOMETRY_CACHE:
        return _GEOMETRY_CACHE[key]

    import healpy as hp

    mask = galactic_edge_mask(nside, b_cut)
    n_dir = hp.nside2npix(nside_dir)
    theta_dir, phi_dir = hp.pix2ang(nside_dir, np.arange(n_dir))
    vec_dir = np.stack(hp.pix2vec(nside_dir, np.arange(n_dir)), axis=1)

    half = np.radians(width_deg / 2.0)
    geometries: list[CircleGeometry] = []
    # Center galactic latitudes, for the mask-hugging guard (map is galactic).
    center_b = np.abs(90.0 - np.degrees(theta_dir))
    for i in range(n_dir):
        for r_deg in radii_deg:
            r = np.radians(r_deg)
            # Guard: the full ring must sit inside the unmasked region, or the
            # "edge" is just the boundary of the Galactic cut. Require the
            # outermost ring pixel to still be above the cut.
            if center_b[i] - (r_deg + width_deg) < b_cut:
                continue
            inner_pix = _ring_pix(nside, vec_dir[i], mask, max(r - half, 0.0), r)
            outer_pix = _ring_pix(nside, vec_dir[i], mask, r, r + half)
            if inner_pix.size < 4 or outer_pix.size < 4:
                continue
            geometries.append(
                CircleGeometry(
                    center_idx=i,
                    theta_rad=float(theta_dir[i]),
                    phi_rad=float(phi_dir[i]),
                    radius_deg=float(r_deg),
                    inner_pix=inner_pix,
                    outer_pix=outer_pix,
                )
            )

    result = (geometries, mask)
    _GEOMETRY_CACHE[key] = result
    return result


def circle_edge_statistic(t_map: np.ndarray, geom: CircleGeometry) -> float:
    """Edge amplitude (µK): mean temperature just outside minus just inside."""
    inner = float(np.mean(t_map[geom.inner_pix]))
    outer = float(np.mean(t_map[geom.outer_pix]))
    return outer - inner


def scan_circle_edges(t_map: np.ndarray, geometries: list[CircleGeometry]) -> np.ndarray:
    """Edge amplitude for every precomputed candidate circle."""
    edges = np.empty(len(geometries))
    for i, geom in enumerate(geometries):
        edges[i] = circle_edge_statistic(t_map, geom)
    return edges


def max_abs_edge(t_map: np.ndarray, geometries: list[CircleGeometry]) -> tuple[float, int]:
    edges = scan_circle_edges(t_map, geometries)
    idx = int(np.argmax(np.abs(edges)))
    return float(edges[idx]), idx


def inject_bubble_collision(
    t_map: np.ndarray,
    center_vec: np.ndarray,
    radius_deg: float,
    amplitude_uk: float,
    nside: int,
    edge_width_deg: float = 2.0,
) -> np.ndarray:
    """Plant a synthetic collision: temperature step across a circular edge.

    Inside the disc the temperature is shifted by ``amplitude_uk`` relative
    to outside, smeared over ``edge_width_deg`` so the step is resolvable at
    the map resolution. Used to validate that the search recovers planted
    collisions (the Gate that proves the instrument works).
    """
    import healpy as hp

    out = np.asarray(t_map, dtype=float).copy()
    npix = hp.nside2npix(nside)
    vecs = np.stack(hp.pix2vec(nside, np.arange(npix)), axis=1)
    cos_theta = np.clip(
        np.einsum("j,ij->i", center_vec / (np.linalg.norm(center_vec) + 1e-15), vecs), -1.0, 1.0
    )
    ang = np.degrees(np.arccos(cos_theta))
    edge_w = max(edge_width_deg, 1e-3)
    profile = 0.5 * (1.0 + np.tanh((radius_deg - ang) / edge_w))
    out = out + amplitude_uk * profile
    return out


def load_planck_for_search(
    map_product_id: str = "planck_smica_cmb",
    nside: int = 128,
    cache: DataCache | None = None,
) -> tuple[np.ndarray, str]:
    """Load a real CMB map downsampled for the scan, in µK.

    Returns (map_uk, product_id). Planck component maps ship in Kelvin;
    maps with peak |T| below 1e-2 are converted to µK.
    """
    from polomni.observatory.pipeline.catalog import get_product
    from polomni.observatory.pipeline.downloader import fetch_product

    cache = cache or DataCache()
    path = cache.resolved_path(map_product_id)
    if path is None:
        product = get_product(map_product_id)
        fetch = fetch_product(product, cache, force=False)
        path = fetch.path
    raw = load_healpix_map(path, field="T")
    down = downsample_map(raw, nside)
    scale = 1e6 if float(np.max(np.abs(down))) < 1e-2 else 1.0
    return down * scale, map_product_id


def bubble_collision_report(
    *,
    map_product_id: str = "planck_smica_cmb",
    nside: int = 128,
    nside_dir: int = 8,
    radii_deg: tuple[float, ...] = (15.0, 25.0, 35.0, 45.0, 55.0, 65.0, 75.0),
    width_deg: float = 5.0,
    b_cut: float = 20.0,
    n_null: int = 24,
    seed: int = 42,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Full bubble-collision search on a real CMB map with honest null.

    Steps
    -----
    1. Load + downsample the real map (µK), apply the Galactic mask.
    2. Precompute circle geometry (centers × radii), cached.
    3. Measure the edge amplitude of every candidate circle.
    4. Build a C_ℓ-matched Gaussian null: simulate maps with the observed
       power spectrum, same mask, same geometry; record the max |edge| per
       realization (the look-elsewhere-corrected null).
    5. p-value = fraction of null realizations whose strongest circle exceeds
       the observed strongest circle (+1 pseudo-count).
    6. Report the top candidates with sky coordinates + a radial profile of
       the strongest candidate (a collision is a *step*: flat inside, flat
       outside, sharp edge).
    """
    import healpy as hp

    t_map, pid = load_planck_for_search(map_product_id=map_product_id, nside=nside, cache=cache)
    geometries, mask = bubble_scan_geometry(
        nside=nside, nside_dir=nside_dir, radii_deg=radii_deg, width_deg=width_deg, b_cut=b_cut
    )

    f_sky = float(np.mean(mask))
    obs_edges = scan_circle_edges(t_map, geometries)

    cl = hp.anafast(t_map, lmax=2 * nside)
    cl[0] = 0.0
    cl[1] = 0.0
    rng = np.random.default_rng(seed)

    null_max: list[float] = []
    null_edges = np.empty((n_null, len(geometries)))
    for i in range(n_null):
        sim = hp.synfast(cl, nside, new=True, pol=False, verbose=False)
        sim = sim * float(np.std(t_map[mask]) / (np.std(sim[mask]) + 1e-12))
        sim_edges = scan_circle_edges(sim, geometries)
        null_edges[i] = sim_edges
        null_max.append(float(np.max(np.abs(sim_edges))))
    null_max_arr = np.asarray(null_max)
    null_sigma = float(np.std(null_max_arr))

    obs_max = float(np.max(np.abs(obs_edges)))
    p_value = float((1 + int(np.sum(null_max_arr >= obs_max))) / (n_null + 1.0))

    order = np.argsort(-np.abs(obs_edges))
    n_top = min(8, len(order))
    candidates = []
    for pos in order[:n_top]:
        geom = geometries[pos]
        theta, phi = geom.theta_rad, geom.phi_rad
        lat = 90.0 - np.degrees(theta)
        lon = np.degrees(phi)
        if lon > 180.0:
            lon -= 360.0
        candidates.append(
            {
                "center_index": int(geom.center_idx),
                "gal_lon": round(lon, 2),
                "gal_lat": round(lat, 2),
                "radius_deg": geom.radius_deg,
                "edge_uk": round(float(obs_edges[pos]), 2),
                "abs_edge_uk": round(float(abs(obs_edges[pos])), 2),
            }
        )

    best = geometries[int(order[0])]
    profile = _radial_profile(t_map, best, nside, mask, max_radius=85.0, n_rings=12)

    top_profile = []
    for r_deg, mean_t, n in zip(profile[0], profile[1], profile[2]):
        top_profile.append({"radius_deg": float(r_deg), "mean_t_uk": float(mean_t), "n_pixels": int(n)})

    return {
        "instrument": "bubble-collision circle-edge search (eternal inflation)",
        "map_product_id": pid,
        "nside": nside,
        "n_centers": int(len(np.unique([g.center_idx for g in geometries]))),
        "n_circles_scanned": int(len(geometries)),
        "mask": {"b_cut_deg": b_cut, "f_sky": round(f_sky, 4)},
        "null": {
            "n_realizations": n_null,
            "max_abs_edge_uk": {
                "observed": round(obs_max, 2),
                "median": round(float(np.median(null_max_arr)), 2),
                "p84": round(float(np.percentile(null_max_arr, 84)), 2),
                "sigma": round(null_sigma, 2),
            },
        },
        "p_value": round(p_value, 4),
        "strongest_circle": {
            "gal_lon": candidates[0]["gal_lon"] if candidates else None,
            "gal_lat": candidates[0]["gal_lat"] if candidates else None,
            "radius_deg": candidates[0]["radius_deg"] if candidates else None,
            "edge_uk": candidates[0]["edge_uk"] if candidates else None,
            "radial_profile": top_profile,
        },
        "top_candidates": candidates,
        "verdict": (
            "No statistically significant circular temperature edge "
            "found — the strongest edge is consistent with the "
            "C_ℓ-matched + mask-matched null."
            if p_value > 0.05
            else "Candidate circular edge above the null — requires "
            "adversarial foreground/excision checks before any claim."
        ),
        "equation": "edge(n̂_c, θ) = ⟨T⟩_{θ..θ+w} − ⟨T⟩_{θ−w..θ}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _radial_profile(
    t_map: np.ndarray,
    geom: CircleGeometry,
    nside: int,
    mask: np.ndarray,
    max_radius: float = 85.0,
    n_rings: int = 12,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean temperature vs angular distance from the circle center (the step)."""
    import healpy as hp

    center_vec = np.stack(
        hp.pix2vec(nside, int(hp.ang2pix(nside, geom.theta_rad, geom.phi_rad))), axis=0
    )
    radii = np.linspace(3.0, max_radius, n_rings)
    means = np.empty(n_rings)
    counts = np.empty(n_rings)
    for i, r in enumerate(radii):
        r_rad = np.radians(r)
        pix = hp.query_disc(nside, center_vec, r_rad, inclusive=True)
        pix = pix[mask[pix]]
        if pix.size == 0:
            means[i] = np.nan
            counts[i] = 0
            continue
        means[i] = float(np.mean(t_map[pix]))
        counts[i] = float(pix.size)
    return radii, means, counts
