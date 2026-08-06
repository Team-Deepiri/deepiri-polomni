"""Cross-sky axis comparison — the two-independent-skies test.

The RBLE multiverse picture predicts a scar locked to a single preferred axis
visible in *every* sky. That claim is falsifiable without trusting any single
survey: take several independent sky datasets (exoplanets, SDSS galaxies,
gravitational-wave events, the CMB), compute each one's dipole and preferred
axis, and ask whether the axes agree.

The null is exactly the World Atlas null: a genuine scar must survive per-sky
footprint checks (the exoplanet sky is Kepler-dominated, SDSS is a northern
cap, GW events are detector-noise-dominated) AND point at a common direction
across skies that share no survey. Each sky gets its own honest null; the
pairwise axis table is the cross-validation.

References/state variables (see docs/theory/WORLD_ATLAS.md):
  - ``reference_alignment_table`` — per-sky dipole vs cosmic rest frames.
  - pairwise axis separation — agreement across unrelated surveys is the only
    evidence that survives selection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.exoplanets import (
    angular_separation_deg,
    radec_to_sky_coords,
    reference_alignment_table,
    reference_directions,
    world_dipole,
)


@dataclass
class SkySample:
    """A named independent sky dataset as unit direction vectors."""

    name: str
    vectors: np.ndarray
    n_objects: int
    note: str


def load_galaxy_vectors(
    catalog: list[dict] | Path | str,
) -> np.ndarray:
    """Unit vectors from an SDSS sky-object catalog (list of ra/dec dicts)."""
    if not isinstance(catalog, (list, tuple)):
        data = json.loads(Path(catalog).read_text())
    else:
        data = catalog
    ra = np.asarray([float(o["ra"]) for o in data])
    dec = np.asarray([float(o["dec"]) for o in data])
    x, y, z = radec_to_sky_coords(ra, dec)
    return np.column_stack([x, y, z])


def load_gw_vectors(events: list[dict] | Path | str) -> np.ndarray:
    """Unit vectors from a GWTC events list (``network_axis`` per event).

    Raises ValueError if the direction set is degenerate — ``network_axis`` is
    the LIGO/Virgo detector-triangle normal (a *constant of the instrument*,
    only a handful of unique values across the whole catalog), not the sky
    direction of each merger. A sky sample whose "directions" don't vary is not
    a sky sample; including it would fake an alignment with any fixed
    reference (e.g. the CMB apex at ~21° from the triangle normal).
    """
    if not isinstance(events, (list, tuple)):
        payload = json.loads(Path(events).read_text())
        events = payload.get("events", payload)
    vecs = np.asarray(
        [np.asarray(e["network_axis"], dtype=float) for e in events],
        dtype=float,
    )
    unique = np.unique(np.round(vecs, 3), axis=0)
    if unique.shape[0] < 0.5 * vecs.shape[0]:
        raise ValueError(
            "GW network_axis is detector geometry, not sky direction: only "
            f"{unique.shape[0]} unique directions across {vecs.shape[0]} events."
        )
    return vecs


def sky_samples(cache: DataCache | None = None) -> list[SkySample]:
    """Load every cached sky dataset as unit vectors.

    Discovery is by direct filesystem probe under the cache root (the manifest
    does not register every product), falling back to ``resolved_path``.
    """
    cache = cache or DataCache()

    def _candidate(rel: str) -> Path | None:
        p = cache.root / rel
        if p.exists():
            return p
        return None

    samples: list[SkySample] = []

    # Exoplanets
    exo_path = (
        cache.resolved_path("nasa_exoplanet_ps")
        or _candidate("nasa_exoplanet_ps/nasa_exoplanet_ps.csv")
    )
    if exo_path is not None:
        from polomni.observatory.pipeline.sources.exoplanets import (
            load_exoplanet_catalog,
            world_vectors,
        )

        cat = load_exoplanet_catalog(exo_path)
        vecs, good = world_vectors(cat)
        samples.append(
            SkySample(
                name="exoplanets",
                vectors=vecs,
                n_objects=int(good.sum()),
                note="NASA confirmed worlds (Kepler/TESS footprint-dominated)",
            )
        )

    # SDSS galaxies
    sdss_resolved = cache.resolved_path("sdss_bao_ladder")
    sdss_candidate = _candidate("sdss_bao_ladder")
    sdss_paths: list[Path] = []
    if sdss_resolved is not None and sdss_resolved.is_file():
        sdss_paths = [sdss_resolved]
    elif sdss_candidate is not None and sdss_candidate.is_dir():
        sdss_paths = [
            sdss_candidate / f
            for f in ("sdss_sky_objects.json", "sdss_bao_ladder.json")
            if (sdss_candidate / f).exists()
        ]
    for p in sdss_paths:
        vecs = load_galaxy_vectors(p)
        samples.append(
            SkySample(
                name="sdss_galaxies",
                vectors=vecs,
                n_objects=int(vecs.shape[0]),
                note="SDSS BAO sample (northern-cap footprint)",
            )
        )
        break

    # Gravitational-wave events
    gw_path = (
        cache.resolved_path("gwtc_events")
        or _candidate("gwtc_events")
    )
    if gw_path is not None:
        if gw_path.is_dir():
            gw_file = gw_path / "gwtc_events.json"
        else:
            gw_file = gw_path
        if gw_file.exists():
            try:
                vecs = load_gw_vectors(gw_file)
            except ValueError as exc:
                samples.append(
                    SkySample(
                        name="gw_events",
                        vectors=np.zeros((0, 3)),
                        n_objects=0,
                        note=f"excluded — {exc}",
                    )
                )
            else:
                samples.append(
                    SkySample(
                        name="gw_events",
                        vectors=vecs,
                        n_objects=int(vecs.shape[0]),
                        note="GWTC merger network axes (detector-sensitivity pattern)",
                    )
                )
    return samples


def sky_dipole_report(sample: SkySample) -> dict[str, object]:
    """Dipole + reference alignment for one sky sample."""
    d, mag = world_dipole(sample.vectors)
    return {
        "sky": sample.name,
        "n_objects": sample.n_objects,
        "note": sample.note,
        "dipole": d.tolist(),
        "magnitude": float(mag),
        "isotropic_expectation": float(1.0 / np.sqrt(3.0 * sample.n_objects)),
        "references": reference_alignment_table(d),
    }


def cross_sky_report(
    cache: DataCache | None = None,
    *,
    min_objects: int = 20,
) -> dict[str, object]:
    """Compare dipoles across all independent skies.

    Returns per-sky dipole reports and a pairwise separation matrix. Axes
    agreeing across *unrelated* surveys (and disagreeing with each survey's own
    footprint) are the only evidence that survives selection.
    """
    samples = [s for s in sky_samples(cache) if s.n_objects >= min_objects]
    reports = [sky_dipole_report(s) for s in samples]
    names = [r["sky"] for r in reports]
    dipoles = np.asarray([r["dipole"] for r in reports], dtype=float)

    pairs: list[dict[str, object]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append(
                {
                    "sky_a": names[i],
                    "sky_b": names[j],
                    "separation_deg": float(
                        angular_separation_deg(dipoles[i], dipoles[j])
                    ),
                }
            )
    return {
        "skies": reports,
        "pairwise": pairs,
        "n_skies": int(len(reports)),
    }
