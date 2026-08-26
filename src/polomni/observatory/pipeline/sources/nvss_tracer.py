"""All-sky dense tracers: NVSS bright radio + mega SDSS LRG strips.

Locksmith: Phase H showed northern SDSS LRG *dilutes* PSCz Fisher SNR.
Outsider loop: NVSS (VIII/65) is nearly all-sky at Dec > −40° — stack bright
S₁.₄ ≥ 200 mJy sources with PSCz instead of footprint-clumped SpecObj.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache

NVSS_PRODUCT = "nvss_bright"
NVSS_VIZIER_URL = (
    "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?"
    "-source=VIII/65/nvss&-out.max=50000&-out=_RAJ2000,_DEJ2000,S1.4&S1.4=%3E%3D200"
)


def parse_nvss_tsv(text: str) -> list[dict[str, float]]:
    """Parse VizieR NVSS TSV into ``{ra, dec, s14}`` (degrees, mJy)."""
    rows: list[dict[str, float]] = []
    for line in text.splitlines():
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if "_RA" in line or "deg" in line or "mJy" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 2:
            continue
        try:
            ra = float(parts[0])
            dec = float(parts[1])
        except ValueError:
            continue
        s14 = float(parts[2]) if len(parts) > 2 and parts[2] not in {"", "---"} else float("nan")
        rows.append({"ra": ra, "dec": dec, "s14": s14})
    return rows


def fetch_nvss_bright(
    *,
    cache: DataCache | None = None,
    timeout: float = 180.0,
    force: bool = False,
) -> Path:
    """Download bright NVSS sources (S≥200 mJy) into the data cache."""
    cache = cache or DataCache()
    dest_dir = cache.root / NVSS_PRODUCT
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{NVSS_PRODUCT}.json"
    if dest.exists() and not force:
        entry = cache.get_entry(NVSS_PRODUCT)
        if entry is not None:
            return dest

    req = urllib.request.Request(NVSS_VIZIER_URL, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    rows = parse_nvss_tsv(text)
    if len(rows) < 500:
        raise RuntimeError(f"NVSS bright fetch too small ({len(rows)})")
    payload = {
        "source": "VIII/65/nvss",
        "flux_cut_mjy": 200.0,
        "n_objects": len(rows),
        "objects": rows,
    }
    dest.write_text(json.dumps(payload), encoding="utf-8")
    cache.record(NVSS_PRODUCT, dest, url=NVSS_VIZIER_URL)
    return dest


def load_nvss_vectors(path: Path | str | None = None) -> np.ndarray:
    """Unit equatorial vectors from cached NVSS bright JSON."""
    from polomni.observatory.pipeline.sources.exoplanets import radec_to_sky_coords

    if path is None:
        cache = DataCache()
        resolved = cache.resolved_path(NVSS_PRODUCT)
        if resolved is None:
            cand = cache.root / NVSS_PRODUCT / f"{NVSS_PRODUCT}.json"
            path = cand if cand.exists() else None
        else:
            path = resolved
    if path is None:
        raise FileNotFoundError("nvss_bright not cached — run fetch_nvss_bright()")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    objs = payload.get("objects") or payload
    ra = np.asarray([float(o["ra"]) for o in objs], dtype=float)
    dec = np.asarray([float(o["dec"]) for o in objs], dtype=float)
    x, y, z = radec_to_sky_coords(ra, dec)
    return np.column_stack([x, y, z])
