"""IRAS PSCz — footprint-light all-sky galaxy tracer for multi-survey scars.

Saunders et al. 2000 PSCz selects IRAS 60µm galaxies over ~84% of the sky
(avoiding only the deepest Galactic plane extinction). Unlike SDSS SpecObj
(northern cap) or Kepler-dominated exoplanets, PSCz is nearly all-sky and is
the classic large-scale structure tracer for dipole / bulk-flow tests.

Fetched via CDS VizieR ASU (VII/221/pscz).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache

PSCZ_VIZIER_URL = (
    "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?"
    "-source=VII/221/pscz&-out.max=20000&-out=_RA.icrs,_DE.icrs,S60,Hvel"
)
PRODUCT_ID = "iras_pscz"


def parse_pscz_tsv(text: str) -> list[dict[str, float]]:
    """Parse VizieR TSV into ``{ra, dec, s60, hvel}`` rows (ICRS degrees)."""
    rows: list[dict[str, float]] = []
    for line in text.splitlines():
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Skip header / unit lines
        if "_RA" in line or "deg" in line or "Jy" in line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 2:
            continue
        try:
            ra = float(parts[0])
            dec = float(parts[1])
        except ValueError:
            continue
        s60 = float(parts[2]) if len(parts) > 2 and parts[2] not in {"", "---"} else float("nan")
        hvel = float(parts[3]) if len(parts) > 3 and parts[3] not in {"", "---"} else float("nan")
        rows.append({"ra": ra, "dec": dec, "s60": s60, "hvel": hvel})
    return rows


def fetch_iras_pscz(
    *,
    cache: DataCache | None = None,
    timeout: float = 120.0,
    force: bool = False,
) -> Path:
    """Download PSCz ICRS positions into the data cache."""
    cache = cache or DataCache()
    dest_dir = cache.root / PRODUCT_ID
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "iras_pscz.json"
    if dest.exists() and not force:
        entry = cache.get_entry(PRODUCT_ID)
        if entry is not None:
            return dest

    req = urllib.request.Request(PSCZ_VIZIER_URL, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    rows = parse_pscz_tsv(text)
    if len(rows) < 100:
        raise RuntimeError(f"PSCz fetch returned too few rows ({len(rows)})")
    payload = {
        "source": "VII/221/pscz",
        "n_objects": len(rows),
        "objects": rows,
    }
    dest.write_text(json.dumps(payload), encoding="utf-8")
    cache.record(PRODUCT_ID, dest, url=PSCZ_VIZIER_URL)
    return dest


def load_pscz_vectors(path: Path | str | None = None) -> np.ndarray:
    """Unit equatorial vectors from a cached PSCz JSON."""
    from polomni.observatory.pipeline.sources.exoplanets import radec_to_sky_coords

    if path is None:
        cache = DataCache()
        resolved = cache.resolved_path(PRODUCT_ID)
        if resolved is None:
            cand = cache.root / PRODUCT_ID / "iras_pscz.json"
            path = cand if cand.exists() else None
        else:
            path = resolved
    if path is None:
        raise FileNotFoundError("iras_pscz not cached — run fetch_iras_pscz()")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    objs = payload.get("objects") or payload
    ra = np.asarray([float(o["ra"]) for o in objs], dtype=float)
    dec = np.asarray([float(o["dec"]) for o in objs], dtype=float)
    x, y, z = radec_to_sky_coords(ra, dec)
    return np.column_stack([x, y, z])


def pscz_report(path: Path | str | None = None) -> dict[str, Any]:
    vecs = load_pscz_vectors(path)
    return {"n_objects": int(vecs.shape[0]), "product_id": PRODUCT_ID}
