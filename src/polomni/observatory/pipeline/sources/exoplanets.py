"""NASA Exoplanet Archive planetary-systems (``ps``) table adapter.

Parses the confirmed-planet CSV from the NASA Exoplanet Archive TAP endpoint
and builds a HEALPix sky-density map of world positions — the input to the
RBLE world-atlas scan (geodesic Radon scar detection over the distribution
of real exoplanets).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RA_COL = "ra"
DEC_COL = "dec"
NAME_COL = "pl_name"
HOST_COL = "hostname"
PERIOD_COL = "pl_orbper"
RADIUS_COL = "pl_rade"
MASS_COL = "pl_bmassj"
ST_TEFF_COL = "st_teff"
EQT_COL = "pl_eqt"
INSOL_COL = "pl_insol"
YEAR_COL = "disc_year"
METHOD_COL = "discoverymethod"


@dataclass
class ExoplanetCatalog:
    """Lightweight columnar catalog of confirmed exoplanets."""

    names: np.ndarray
    hosts: np.ndarray
    ra: np.ndarray  # degrees, ICRS
    dec: np.ndarray  # degrees, ICRS
    period_days: np.ndarray
    radius_earth: np.ndarray
    mass_jup: np.ndarray
    st_teff: np.ndarray
    eq_temp: np.ndarray
    insol_flux: np.ndarray
    disc_year: np.ndarray
    method: np.ndarray

    def __len__(self) -> int:
        return int(self.ra.size)


def _as_float_array(values: list[str]) -> np.ndarray:
    out: list[float] = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(float("nan"))
    return np.asarray(out, dtype=float)


def load_exoplanet_catalog(path: str | Path) -> ExoplanetCatalog:
    """Parse the NASA Exoplanet Archive ``ps`` CSV export."""
    path = Path(path)
    names: list[str] = []
    hosts: list[str] = []
    ra: list[str] = []
    dec: list[str] = []
    period: list[str] = []
    radius: list[str] = []
    mass: list[str] = []
    teff: list[str] = []
    eqt: list[str] = []
    insol: list[str] = []
    year: list[str] = []
    method: list[str] = []

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ra_str = row.get(RA_COL, "").strip()
            dec_str = row.get(DEC_COL, "").strip()
            if ra_str in ("", "None") or dec_str in ("", "None"):
                continue
            try:
                float(ra_str)
                float(dec_str)
            except ValueError:
                continue
            names.append(row.get(NAME_COL, ""))
            hosts.append(row.get(HOST_COL, ""))
            ra.append(row.get(RA_COL, ""))
            dec.append(row.get(DEC_COL, ""))
            period.append(row.get(PERIOD_COL, ""))
            radius.append(row.get(RADIUS_COL, ""))
            mass.append(row.get(MASS_COL, ""))
            teff.append(row.get(ST_TEFF_COL, ""))
            eqt.append(row.get(EQT_COL, ""))
            insol.append(row.get(INSOL_COL, ""))
            year.append(row.get(YEAR_COL, ""))
            method.append(row.get(METHOD_COL, ""))

    if not names:
        raise ValueError(f"No exoplanet rows parsed from {path}")

    return ExoplanetCatalog(
        names=np.asarray(names),
        hosts=np.asarray(hosts),
        ra=_as_float_array(ra),
        dec=_as_float_array(dec),
        period_days=_as_float_array(period),
        radius_earth=_as_float_array(radius),
        mass_jup=_as_float_array(mass),
        st_teff=_as_float_array(teff),
        eq_temp=_as_float_array(eqt),
        insol_flux=_as_float_array(insol),
        disc_year=_as_float_array(year),
        method=np.asarray(method),
    )


def radec_to_sky_coords(
    ra: np.ndarray, dec: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Equatorial RA/Dec → unit vectors (x, y, z) on the sphere."""
    ra = np.asarray(ra, dtype=float)
    dec = np.asarray(dec, dtype=float)
    phi = np.radians(ra)
    theta = np.radians(90.0 - dec)
    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)
    return x, y, z


def radec_to_lonlat(ra: np.ndarray, dec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Equatorial RA/Dec → equirectangular lon/lat for plotting."""
    lon = np.asarray(ra, dtype=float)
    lat = np.asarray(dec, dtype=float)
    return lon, lat


def exoplanet_density_map(
    catalog: ExoplanetCatalog,
    nside: int,
    *,
    weight: str = "count",
) -> tuple[np.ndarray, list[float], list[int]]:
    """Bin world positions into a HEALPix density map at *nside*.

    ``weight='count'`` counts worlds per pixel; ``weight='teff'`` accumulates
    host-star temperature (proxy for spectral class mass). Returns the map,
    the HEALPix pixel indices used, and the per-pixel counts.
    """
    import healpy as hp

    npix = hp.nside2npix(nside)
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    x, y, z = radec_to_sky_coords(catalog.ra[good], catalog.dec[good])
    pix = hp.vec2pix(nside, x, y, z)

    if weight == "teff":
        vals = np.nan_to_num(catalog.st_teff[good], nan=0.0)
        total = vals.sum()
        if total <= 0:
            vals = np.ones_like(vals)
        counts = np.bincount(pix, weights=vals, minlength=npix)
    else:
        counts = np.bincount(pix, minlength=npix)

    counts = counts.astype(float)
    if counts.sum() > 0:
        counts = counts / counts.max()
    return counts, [int(p) for p in np.unique(pix)], good.sum().item()


def sky_occupancy_counts(
    catalog: ExoplanetCatalog, nside: int
) -> tuple[int, int, float]:
    """(n_planets, n_occupied_pixels, occupancy_fraction)."""
    import healpy as hp

    npix = hp.nside2npix(nside)
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    x, y, z = radec_to_sky_coords(catalog.ra[good], catalog.dec[good])
    pix = hp.vec2pix(nside, x, y, z)
    return int(good.sum()), int(np.unique(pix).size), np.unique(pix).size / float(npix)


def world_vectors(
    catalog: ExoplanetCatalog,
) -> tuple[np.ndarray, np.ndarray]:
    """Unit vectors of every world with valid RA/Dec, plus their valid mask."""
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    x, y, z = radec_to_sky_coords(catalog.ra[good], catalog.dec[good])
    return np.column_stack([x, y, z]), good


# J2000 reference directions (equatorial cartesians). The CMB dipole apex is
# the direction of the Solar System's motion through the CMB rest frame — the
# one direction a *physical* world-distribution anisotropy must point at if
# worlds trace large-scale structure. Survey artifacts point elsewhere
# (Kepler field, ecliptic pole, Galactic plane).
_CMB_DIPOLE_RA = 167.942  # Planck 2018, equatorial
_CMB_DIPOLE_DEC = -6.944
_ECLIPTIC_NPOLE_RA = 270.0
_ECLIPTIC_NPOLE_DEC = 66.56
_KEPLER_FIELD_RA = 290.5
_KEPLER_FIELD_DEC = 44.5


def _unit_vec(ra: float, dec: float) -> np.ndarray:
    phi = np.radians(ra)
    theta = np.radians(90.0 - dec)
    return np.array(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)],
        dtype=float,
    )


def reference_directions() -> dict[str, np.ndarray]:
    """Named sky reference directions used for the world-dipole alignment test."""
    refs = {
        "CMB_dipole_apex": _unit_vec(_CMB_DIPOLE_RA, _CMB_DIPOLE_DEC),
        "ecliptic_north_pole": _unit_vec(_ECLIPTIC_NPOLE_RA, _ECLIPTIC_NPOLE_DEC),
        "kepler_field_center": _unit_vec(_KEPLER_FIELD_RA, _KEPLER_FIELD_DEC),
    }
    refs["galactic_north_pole"] = galactic_pole_vector()
    return refs


def world_dipole(vecs: np.ndarray) -> tuple[np.ndarray, float]:
    """Dipole of a world-direction set: mean unit vector + |D| magnitude.

    D̂ = ⟨n⟩/|⟨n⟩| is the first spherical-harmonic moment of the distribution
    (the direction the distribution leans toward). |⟨n⟩| ∈ [0,1] is the
    dipole strength: 0 for a perfectly isotropic sample, 1 for a fully
    concentrated one.
    """
    n = np.asarray(vecs, dtype=float)
    mean = n.mean(axis=0)
    mag = float(np.linalg.norm(mean))
    if mag < 1e-12:
        return np.array([1.0, 0.0, 0.0]), 0.0
    return mean / mag, mag


def dipole_bootstrap(
    catalog: ExoplanetCatalog,
    *,
    n_boot: int = 200,
    seed: int = 7,
) -> dict[str, object]:
    """Bootstrap the world-dipole direction for the full sample.

    Resamples worlds with replacement and recomputes the dipole each time;
    returns the mean separation of bootstrap dipoles from the observed dipole
    (68% confidence radius, degrees).
    """
    vecs, good = world_vectors(catalog)
    observed, mag = world_dipole(vecs)
    rng = np.random.default_rng(seed)
    separations: list[float] = []
    directions: list[list[float]] = []
    n = vecs.shape[0]
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        d, _ = world_dipole(vecs[idx])
        directions.append(d.tolist())
        separations.append(angular_separation_deg(observed, d))
    separations = np.asarray(separations)
    return {
        "n_boot": n_boot,
        "observed_dipole": observed.tolist(),
        "observed_magnitude": mag,
        "sigma68_deg": float(np.percentile(separations, 68)),
        "median_deg": float(np.median(separations)),
        "directions": directions,
    }


def reference_alignment_table(
    dipole: np.ndarray,
    refs: dict[str, np.ndarray] | None = None,
) -> dict[str, dict[str, float]]:
    """Angular separation of *dipole* from each named reference direction."""
    refs = refs or reference_directions()
    out: dict[str, dict[str, float]] = {}
    for name, ref_vec in refs.items():
        out[name] = {"separation_deg": float(angular_separation_deg(dipole, ref_vec))}
    return out


def alignment_tensor(world_vecs: np.ndarray) -> np.ndarray:
    """Nematic order tensor Q_ab = ⟨n_a n_b⟩ over world directions.

    Exact invariants (see docs/theory/WORLD_ATLAS.md):
      - Tr(Q) = 1 for any sample (trace of the outer-product mean).
      - Q is symmetric, so it always diagonalizes with real eigenvalues.
    """
    n = np.asarray(world_vecs, dtype=float)
    return (n.T @ n) / max(n.shape[0], 1)


def alignment_decomposition(
    catalog: ExoplanetCatalog,
) -> dict[str, object]:
    """Eigen-decomposition of the world alignment tensor + order parameter."""
    vecs, _ = world_vectors(catalog)
    q = alignment_tensor(vecs)
    evals, evecs = np.linalg.eigh(q)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    lam1 = evals[0]
    s_order = 0.5 * (3.0 * lam1 - 1.0)
    return {
        "n_worlds": int(vecs.shape[0]),
        "trace": float(np.trace(q)),
        "eigenvalues": evals.tolist(),
        "eigenvectors": evecs.T.tolist(),
        "preferred_axis": evecs[:, 0].tolist(),
        "order_parameter_s": float(s_order),
        "lam1_minus_isotropic": float(lam1 - 1.0 / 3.0),
    }


def method_alignment_scan(
    catalog: ExoplanetCatalog,
    min_worlds: int = 50,
) -> dict[str, dict[str, object]]:
    """Per-discovery-method alignment decomposition (selection-bias audit).

    A scar that is real physics — not a survey footprint — should persist
    across methods with different sky coverage. Transit samples are dominated
    by the Kepler field footprint; radial-velocity samples are near
    sky-complete. Comparing their preferred axes is the adversarial check.
    """
    vecs, good = world_vectors(catalog)
    out: dict[str, dict[str, object]] = {}
    for method in np.unique(catalog.method):
        mask = good & (catalog.method == method)
        if mask.sum() < min_worlds:
            continue
        sub = vecs[mask]
        q = alignment_tensor(sub)
        evals, evecs = np.linalg.eigh(q)
        order = np.argsort(evals)[::-1]
        evals = evals[order]
        evecs = evecs[:, order]
        out[str(method)] = {
            "n_worlds": int(mask.sum()),
            "order_parameter_s": float(0.5 * (3.0 * evals[0] - 1.0)),
            "preferred_axis": evecs[:, 0].tolist(),
            "eigenvalues": evals.tolist(),
        }
    return out


def method_dipole_scan(
    catalog: ExoplanetCatalog,
    *,
    min_worlds: int = 50,
    n_boot: int = 100,
    seed: int = 7,
) -> dict[str, dict[str, object]]:
    """Per-discovery-method dipole: direction, strength, and 68% bootstrap cone.

    Complements method_alignment_scan with the error budget a publishable
    claim needs: each method's dipole direction, its magnitude (0 = isotropic,
    1 = fully concentrated), and sigma68 — the 68th percentile of bootstrap
    dipole separations — plus the separation from each reference direction.
    """
    vecs, good = world_vectors(catalog)
    refs = reference_directions()
    rng = np.random.default_rng(seed)
    out: dict[str, dict[str, object]] = {}
    for method in np.unique(catalog.method):
        mask = good & (catalog.method == method)
        if mask.sum() < min_worlds:
            continue
        sub = vecs[mask]
        observed, mag = world_dipole(sub)
        n = sub.shape[0]
        seps = []
        for _ in range(n_boot):
            idx = rng.integers(0, n, size=n)
            d, _ = world_dipole(sub[idx])
            seps.append(angular_separation_deg(observed, d))
        seps = np.asarray(seps)
        refs_out = {
            name: float(angular_separation_deg(observed, ref))
            for name, ref in refs.items()
        }
        out[str(method)] = {
            "n_worlds": int(mask.sum()),
            "dipole": observed.tolist(),
            "magnitude": float(mag),
            "sigma68_deg": float(np.percentile(seps, 68)),
            "median_deg": float(np.median(seps)),
            "references": refs_out,
        }
    return out


def angular_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    """Angle (degrees) between two unit vectors, robust to antiparallel axes."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a / np.linalg.norm(a) if np.linalg.norm(a) > 0 else a
    b = b / np.linalg.norm(b) if np.linalg.norm(b) > 0 else b
    mu = float(np.clip(np.abs(a @ b), 0.0, 1.0))
    return float(np.degrees(np.arccos(mu)))


# Galactic north pole (J2000) in equatorial cartesian units — the reference a
# genuine world scar must be distinguishable from our own Galaxy's plane.
_GALACTIC_NORTH_POLE_EQU = None


def galactic_pole_vector() -> np.ndarray:
    """Unit vector toward the Galactic north pole in equatorial cartesians.

    RA = 192.8595°, Dec = +27.1283° (J2000). Any axis aligned with this points
    along the Milky Way's angular-momentum axis, i.e. the disk plane's normal.
    """
    global _GALACTIC_NORTH_POLE_EQU
    if _GALACTIC_NORTH_POLE_EQU is None:
        ra = np.radians(192.8595)
        dec = np.radians(27.1283)
        _GALACTIC_NORTH_POLE_EQU = np.array(
            [
                np.cos(dec) * np.cos(ra),
                np.cos(dec) * np.sin(ra),
                np.sin(dec),
            ]
        )
    return _GALACTIC_NORTH_POLE_EQU


def footprint_permuted_density_map(
    catalog: ExoplanetCatalog,
    nside: int,
    rng: np.random.Generator,
    *,
    weight: str = "count",
) -> np.ndarray:
    """One footprint-matched null map: world counts reshuffled within the mask.

    The survey occupancy (which pixels can be occupied) is preserved exactly;
    the count *values* are permuted among occupied pixels. This is the honest
    null for an axis claim, because an isotropic random sky is not reachable —
    the Kepler/TESS footprint already breaks isotropy.
    """
    import healpy as hp

    npix = hp.nside2npix(nside)
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    x, y, z = radec_to_sky_coords(catalog.ra[good], catalog.dec[good])
    pix = hp.vec2pix(nside, x, y, z)
    occupied = np.unique(pix)

    if weight == "teff":
        vals = np.nan_to_num(catalog.st_teff[good], nan=0.0)
    elif weight == "period":
        vals = np.nan_to_num(np.log10(catalog.period_days[good]), nan=0.0)
    else:
        vals = np.ones(good.sum())

    per_pixel = np.bincount(pix, weights=vals, minlength=npix)[occupied]
    permuted = rng.permutation(per_pixel)
    null_map = np.zeros(npix)
    null_map[occupied] = permuted
    if null_map.max() > 0:
        null_map /= null_map.max()
    return null_map


def world_power_spectrum(
    catalog: ExoplanetCatalog,
    nside: int,
    *,
    weight: str = "count",
    lmax: int | None = None,
) -> dict[str, object]:
    """Angular power spectrum C_l of the world sky, mask-corrected.

    This is the novel observable of the research thread: no published C_l
    exists for the *confirmed-planet* sky. We compute pseudo-C_l via HEALPix
    ``anafast`` on the density map and correct for the survey footprint by
    dividing by the window power spectrum (MASTER approximation, order-0:
    C_l^est ≈ C_l^obs / W_l, W_l the power of the occupancy mask).

    Caveats shipped with the result (honesty over hype):
      - ``pseudo`` is the raw transform, ``masked`` the footprint-corrected one.
      - Multipoles below the survey's angular resolution (l ≲ 8 for the
        Kepler/TESS footprint) cannot be measured; the mask variance dominates.
      - A non-white C_l is *not* evidence of a scar — it must clear the
        footprint-permutation null band per-l (see spectrum_null_percentiles).
    """
    import healpy as hp

    lmax = lmax or 3 * nside - 1
    density, occupied_pix, _ = exoplanet_density_map(catalog, nside, weight=weight)
    mask = np.zeros_like(density)
    mask[occupied_pix] = 1.0

    pseudo = hp.anafast(density, lmax=lmax)
    w_pseudo = hp.anafast(mask, lmax=lmax)
    ell = np.arange(len(pseudo))
    with np.errstate(divide="ignore", invalid="ignore"):
        window = np.where(w_pseudo > 1e-12, w_pseudo, np.nan)
        masked = np.where(w_pseudo > 1e-12, pseudo / window, np.nan)
    return {
        "nside": int(nside),
        "lmax": int(lmax),
        "weight": weight,
        "ell": ell.tolist(),
        "pseudo": pseudo.tolist(),
        "window": w_pseudo.tolist(),
        "masked": masked.tolist(),
        "n_occupied_pixels": int(len(occupied_pix)),
        "occupancy_fraction": float(len(occupied_pix) / hp.nside2npix(nside)),
    }


def spectrum_null_percentiles(
    catalog: ExoplanetCatalog,
    nside: int,
    *,
    weight: str = "count",
    lmax: int | None = None,
    n_null: int = 100,
    seed: int = 11,
) -> dict[str, object]:
    """Uniform-within-footprint null band for the world power spectrum.

    Each null map keeps the *observed occupancy mask fixed* but reassigns
    every world to a uniformly random occupied pixel — destroying all spatial
    structure while preserving (a) how many worlds exist and (b) where the
    survey could see them. This is the honest null: an isotropic sky is
    unreachable because the Kepler/TESS footprint already breaks isotropy, so
    the question asked is *"given this footprint, is the world placement
    clumped beyond random?"*.

    Returns, per multipole: the 16/50/84 percentiles of the null pseudo-C_l,
    the tail p-value (fraction of null maps with C_l >= observed), and the
    z-score in units of the null standard deviation.

    Interpretation guard: at low l the null variance is dominated by the fixed
    mask, so small z there is a footprint statement, not a scar. Only
    multipoles with small p-value and z beyond the null scatter deserve a
    physical reading — and even then, compare against the per-method audit.
    """
    import healpy as hp

    density, occupied_pix, _ = exoplanet_density_map(catalog, nside, weight=weight)
    lmax = lmax or 3 * nside - 1
    rng = np.random.default_rng(seed)
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    n_worlds = int(good.sum())
    occupied = np.asarray(occupied_pix)
    n_occ = occupied.size

    if weight == "teff":
        vals = np.nan_to_num(catalog.st_teff[good], nan=0.0)
        total = vals.sum()
        if total <= 0:
            vals = np.ones(n_worlds)
    elif weight == "period":
        vals = np.nan_to_num(np.log10(catalog.period_days[good]), nan=0.0)
    else:
        vals = np.ones(n_worlds)

    x, y, z = radec_to_sky_coords(catalog.ra[good], catalog.dec[good])
    observed_pix = hp.vec2pix(nside, x, y, z)
    npix = hp.nside2npix(nside)
    observed_counts = np.bincount(observed_pix, weights=vals, minlength=npix)

    band = np.zeros((n_null, lmax + 1))
    for i in range(n_null):
        assigned = occupied[rng.integers(0, n_occ, size=n_worlds)]
        null_map = np.zeros(npix)
        if weight == "count":
            np.add.at(null_map, assigned, 1.0)
        else:
            np.add.at(null_map, assigned, vals)
        if null_map.max() > 0:
            null_map /= null_map.max()
        band[i] = hp.anafast(null_map, lmax=lmax)

    obs = hp.anafast(density, lmax=lmax)
    p16 = np.percentile(band, 16, axis=0)
    p50 = np.percentile(band, 50, axis=0)
    p84 = np.percentile(band, 84, axis=0)
    mean = band.mean(axis=0)
    std = band.std(axis=0)
    z = np.where(std > 1e-15, (obs - mean) / std, 0.0)
    p_val = np.asarray([(band[:, i] >= obs[i]).mean() for i in range(len(obs))])
    return {
        "nside": int(nside),
        "lmax": int(lmax),
        "weight": weight,
        "n_null": int(n_null),
        "n_worlds": int(n_worlds),
        "ell": np.arange(lmax + 1).tolist(),
        "p16": p16.tolist(),
        "p50": p50.tolist(),
        "p84": p84.tolist(),
        "observed": obs.tolist(),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "z_score": z.tolist(),
        "p_value": p_val.tolist(),
    }
