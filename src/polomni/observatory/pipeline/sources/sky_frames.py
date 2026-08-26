"""Sky coordinate-frame helpers for multi-survey scar work.

WMAP/Planck HEALPix maps ship in **Galactic** coordinates. NASA Exoplanet
Archive and SDSS positions are **equatorial** (ICRS/J2000). Comparing a CMB
preferred axis to catalog vectors without a frame transform guarantees
disagreement — the axes live on different spheres.

All cross-survey comparisons must share one frame. Default: convert catalog
vectors into Galactic so they meet the native CMB map frame.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

SkyFrame = Literal["galactic", "equatorial"]


def _unit_rows(vecs: np.ndarray) -> np.ndarray:
    v = np.asarray(vecs, dtype=float)
    if v.ndim == 1:
        n = np.linalg.norm(v) + 1e-15
        return v / n
    n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-15
    return v / n


def rotate_sky_vectors(
    vecs: np.ndarray,
    *,
    from_frame: SkyFrame,
    to_frame: SkyFrame,
) -> np.ndarray:
    """Rotate unit vectors between equatorial (C) and Galactic (G).

    Uses healpy ``Rotator(coord=[from, to])`` on (theta, phi).
    """
    if from_frame == to_frame:
        return _unit_rows(vecs)

    import healpy as hp

    code = {"equatorial": "C", "galactic": "G"}
    rot = hp.Rotator(coord=[code[from_frame], code[to_frame]])
    v = np.asarray(vecs, dtype=float)
    single = v.ndim == 1
    if single:
        v = v.reshape(1, 3)
    v = _unit_rows(v)
    theta, phi = hp.vec2ang(v)
    theta_t, phi_t = rot(theta, phi)
    out = np.asarray(hp.ang2vec(theta_t, phi_t), dtype=float)
    if out.ndim == 1:
        out = out.reshape(1, 3)
    # ang2vec may return (3,N) depending on healpy version
    if out.shape[0] == 3 and out.shape[1] != 3:
        out = out.T
    out = _unit_rows(out)
    return out[0] if single else out


def equatorial_to_galactic(vecs: np.ndarray) -> np.ndarray:
    return rotate_sky_vectors(vecs, from_frame="equatorial", to_frame="galactic")


def galactic_to_equatorial(vecs: np.ndarray) -> np.ndarray:
    return rotate_sky_vectors(vecs, from_frame="galactic", to_frame="equatorial")


def axis_lonlat_in_frame(
    axis: np.ndarray, *, frame: SkyFrame
) -> tuple[float, float, str]:
    """Longitude/latitude of *axis* interpreted in *frame* (degrees)."""
    import healpy as hp

    a = _unit_rows(np.asarray(axis, dtype=float).ravel())
    theta, phi = hp.vec2ang(a)
    lat = float(90.0 - float(np.degrees(np.atleast_1d(theta)[0])))
    lon = float(float(np.degrees(np.atleast_1d(phi)[0])) % 360.0)
    label = "galactic (l,b)" if frame == "galactic" else "equatorial (RA,Dec)"
    return lon, lat, label
