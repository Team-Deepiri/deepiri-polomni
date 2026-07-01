"""Unified real-sky catalog overlays for telescope / survey viewers."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Literal

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import GWOSC_EVENTS_PRODUCT_ID, get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.sources.gwosc import load_cached_gwtc
from polomni.viz.cosmos.raster import sky_overlays_geojson

SkyFrame = Literal["galactic", "equatorial"]

# HiPS surveys served by CDS (used by ESASky, Aladin, IVOA standard).
SURVEY_CATALOG: dict[str, dict[str, str]] = {
    "dss2": {
        "id": "P/DSS2/color",
        "name": "DSS2 Color (optical all-sky)",
        "mission": "DSS / POSS",
        "band": "optical",
    },
    "2mass": {
        "id": "P/2MASS/color",
        "name": "2MASS All-Sky (near-IR)",
        "mission": "2MASS",
        "band": "near-ir",
    },
    "wise": {
        "id": "P/allWISE/color",
        "name": "AllWISE (mid-IR)",
        "mission": "WISE",
        "band": "mid-ir",
    },
    "planck143": {
        "id": "P/planck/HFI/143",
        "name": "Planck HFI 143 GHz",
        "mission": "Planck",
        "band": "microwave",
    },
    "cmb_wmap": {
        "id": "polomni-cmb-wmap",
        "name": "WMAP Ka-band CMB (Polomni raster)",
        "mission": "WMAP",
        "band": "cmb",
    },
    "cmb_planck": {
        "id": "polomni-cmb-planck",
        "name": "Planck SMICA CMB (Polomni raster)",
        "mission": "Planck",
        "band": "cmb",
    },
}


def cartesian_to_radec(axis: list[float] | np.ndarray) -> tuple[float, float]:
    """Unit 3-vector → ICRS (RA deg, Dec deg)."""
    v = np.asarray(axis, dtype=float).ravel()
    v = v / (np.linalg.norm(v) + 1e-15)
    dec = float(np.degrees(np.arcsin(np.clip(v[2], -1.0, 1.0))))
    ra = float(np.degrees(np.arctan2(v[1], v[0])) % 360.0)
    return ra, dec


def cartesian_to_galactic(axis: list[float] | np.ndarray) -> tuple[float, float]:
    """Unit 3-vector → galactic (l, b) degrees."""
    import healpy as hp

    v = np.asarray(axis, dtype=float).ravel()
    v = v / (np.linalg.norm(v) + 1e-15)
    theta, phi = hp.vec2ang(v)
    b = float(90.0 - np.degrees(theta)[0])
    lon = float(np.degrees(phi)[0])
    return lon, b


def _sdss_specobj_query(*, limit: int = 80) -> list[dict[str, Any]]:
    """Fetch SDSS spectroscopic objects with sky positions (public SkyServer API)."""
    sql = (
        f"SELECT TOP {limit} ra, dec, z "
        "FROM SpecObj WHERE z BETWEEN 0.05 AND 1.2 ORDER BY z DESC"
    )
    cmd = urllib.parse.quote(sql)
    url = (
        "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
        f"?format=json&cmd={cmd}"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for table in payload:
            if isinstance(table, dict) and table.get("TableName") == "Table1":
                rows = list(table.get("Rows", []))
                break
    elif isinstance(payload, dict):
        rows = list(payload.get("Rows", []))
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "ra": float(row["ra"]),
                "dec": float(row["dec"]),
                "z": float(row["z"]),
                "kind": str(row.get("bestClass", "galaxy")).lower(),
            }
        )
    return out


def _sdss_with_galactic(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach galactic lon/lat to SDSS ICRS positions."""
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u

        out: list[dict[str, Any]] = []
        for o in objects:
            c = SkyCoord(ra=o["ra"] * u.deg, dec=o["dec"] * u.deg, frame="icrs")
            g = c.galactic
            out.append(
                {
                    **o,
                    "glon": float(g.l.deg),
                    "glat": float(g.b.deg),
                }
            )
        return out
    except ImportError:
        return objects


def sdss_sky_objects(*, cache: DataCache | None = None, limit: int = 80) -> list[dict[str, Any]]:
    """SDSS galaxies/quasars with live fetch + JSON cache fallback."""
    cache = cache or DataCache()
    product_id = "sdss_bao_ladder"
    path = cache.resolved_path(product_id)
    try:
        objects = _sdss_specobj_query(limit=limit)
        dest_dir = cache.root / product_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "sdss_sky_objects.json"
        dest.write_text(json.dumps(objects, indent=2))
        cache.record(product_id, dest, get_product(product_id).url, extra={"count": len(objects)})
        return _sdss_with_galactic(objects)
    except (OSError, urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError):
        if path is not None and path.exists():
            try:
                cached = json.loads(path.read_text())
                if isinstance(cached, list) and cached and "ra" in cached[0]:
                    return _sdss_with_galactic(cached[:limit])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        try:
            product = get_product(product_id)
            fetch = fetch_product(product, cache, force=False)
            legacy = json.loads(fetch.path.read_text())
            rows = legacy.get("Rows", legacy if isinstance(legacy, list) else [])
            return _sdss_with_galactic(
                [
                    {
                        "ra": float(r["ra"]),
                        "dec": float(r["dec"]),
                        "z": float(r.get("z", 0)),
                        "kind": str(r.get("bestClass", "galaxy")).lower(),
                    }
                    for r in rows
                    if "ra" in r and "dec" in r
                ][:limit]
            )
        except (OSError, KeyError, ValueError, json.JSONDecodeError, TypeError):
            return []


def gw_sky_events(*, cache: DataCache | None = None, limit: int = 40) -> list[dict[str, Any]]:
    """GWTC events with equatorial + galactic sky positions."""
    cache = cache or DataCache()
    snap = load_cached_gwtc(cache)
    if snap is None:
        return []
    events: list[dict[str, Any]] = []
    for ev in snap.events[:limit]:
        if not ev.network_axis:
            continue
        ra, dec = cartesian_to_radec(ev.network_axis)
        glon, glat = cartesian_to_galactic(ev.network_axis)
        events.append(
            {
                "name": ev.name,
                "gps": ev.gps,
                "catalog": ev.catalog,
                "detectors": ev.detectors,
                "ra": ra,
                "dec": dec,
                "glon": glon,
                "glat": glat,
                "network_axis": ev.network_axis,
            }
        )
    return events


def cosmos_world_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    frame: SkyFrame = "galactic",
    force: bool = False,
) -> dict[str, Any]:
    """Full sky world model: surveys, RBLE overlays, GW + SDSS catalogs."""
    overlays = sky_overlays_geojson(
        map_product_id=map_product_id,
        nside=nside,
        force=force,
    )
    gw = gw_sky_events(limit=50)
    sdss = sdss_sky_objects(limit=80)

    scar_ring = overlays["features"][0]["geometry"]["coordinates"]
    axis = overlays["features"][1]["geometry"]["coordinates"]

    if frame == "equatorial":
        # Convert galactic ring/axis to equatorial for Aladin ICRS mode.
        import healpy as hp

        def _g2e(lon: float, lat: float) -> list[float]:
            theta = np.radians(90.0 - lat)
            phi = np.radians(lon)
            vec = np.array(hp.ang2vec(theta, phi))
            ra, dec = cartesian_to_radec(vec)
            return [ra, dec]

        ring_eq = [_g2e(lon, lat) for lon, lat in scar_ring]
        axis_eq = _g2e(axis[0], axis[1])
        ring_frame = ring_eq
        axis_frame = axis_eq
    else:
        ring_frame = scar_ring
        axis_frame = axis

    return {
        "frame": frame,
        "surveys": SURVEY_CATALOG,
        "default_survey": "dss2",
        "cmb_products": {
            "wmap_k_band": "cmb_wmap",
            "planck_smica_cmb": "cmb_planck",
        },
        "rble": {
            "metadata": overlays.get("metadata", {}),
            "scar_ring": ring_frame,
            "axis": axis_frame,
        },
        "gw_events": gw,
        "sdss_objects": sdss,
        "live": {
            "gw_stream": "/stream/gw/poll",
            "cosmos_live": "/cosmos/live",
        },
        "cv": {
            "scan_endpoint": "/observatory/scan",
            "pipeline_endpoint": "/observatory/pipeline",
        },
    }
