"""Parse Planck ancillary cosmology text products."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class PowerSpectrum:
    ell: np.ndarray
    dl: np.ndarray
    dl_err_low: np.ndarray
    dl_err_high: np.ndarray
    best_fit: np.ndarray


def load_planck_tt_power(path: str | Path) -> PowerSpectrum:
    """Load Planck binned C_l^TT file (COM_PowerSpect_CMB-TT-binned)."""
    data = np.loadtxt(path, comments="#")
    return PowerSpectrum(
        ell=data[:, 0],
        dl=data[:, 1],
        dl_err_low=data[:, 2],
        dl_err_high=data[:, 3],
        best_fit=data[:, 4],
    )


def load_camb_lcdm_cl(path: str | Path) -> PowerSpectrum:
    """Load CAMB ΛCDM theory TT spectrum (Planck ancillary, l + TT columns)."""
    data = np.loadtxt(path, comments="#")
    tt = data[:, 1]
    zeros = np.zeros_like(tt)
    return PowerSpectrum(
        ell=data[:, 0],
        dl=tt,
        dl_err_low=zeros,
        dl_err_high=zeros,
        best_fit=tt,
    )


@dataclass
class CosmoParams:
    params: dict[str, float]


def load_planck_cosmo_params(path: str | Path) -> CosmoParams:
    """Parse Planck base-ΛCDM parameter file (key = value lines)."""
    params: dict[str, float] = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.split()[0].strip()
        try:
            params[key] = float(val)
        except ValueError:
            continue
    return CosmoParams(params=params)


# Planck 2018 TT,TE,EE+lowE+lensing+BAO best-fit (arXiv:1807.06209 Table 2).
PLANCK_2018_LCDM: dict[str, float] = {
    "H0": 67.36,
    "omegab": 0.02237,
    "omegac": 0.1200,
    "omegal": 0.6847,
    "ns": 0.9649,
    "sigma8": 0.8111,
}


def lambda_from_planck(params: CosmoParams | None = None) -> float:
    """Extract Λ proxy from Planck parameters (Ω_Λ × h² scale)."""
    if params is None:
        p = PLANCK_2018_LCDM
    else:
        p = params.params
    omega_lambda = p.get("omegal", p.get("Omega_Lambda", 0.6847))
    h = p.get("H0", 67.36) / 100.0
    return float(omega_lambda * h * h)
