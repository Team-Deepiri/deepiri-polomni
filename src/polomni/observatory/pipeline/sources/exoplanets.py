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
