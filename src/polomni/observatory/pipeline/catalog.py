"""Canonical online data products for the RBLE observatory pipeline.

Each product maps to a public NASA/ESA/GWOSC endpoint used in multiverse
falsification work (CMB scars, directed diffusion calibration, GW ringdown).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProductKind = Literal["fits", "txt", "json", "csv"]
ProductTier = Literal["lite", "standard", "heavy"]


@dataclass(frozen=True, slots=True)
class DataProduct:
    """A fetchable cosmology data product."""

    id: str
    name: str
    url: str
    kind: ProductKind
    tier: ProductTier
    description: str
    mission: str
    refresh_hours: float = 24.0 * 7  # re-fetch after 1 week by default
    filename: str | None = None  # override cached filename

    def cache_filename(self) -> str:
        if self.filename:
            return self.filename
        suffix = {"fits": ".fits", "txt": ".txt", "json": ".json", "csv": ".csv"}[self.kind]
        return f"{self.id}{suffix}"


# IRSA Planck Legacy Archive + NASA LAMBDA + GWOSC (public, no API key).
CATALOG: dict[str, DataProduct] = {
    "planck_cmb_tt_power": DataProduct(
        id="planck_cmb_tt_power",
        name="Planck DR3 CMB TT power spectrum (binned)",
        url=(
            "https://irsa.ipac.caltech.edu/data/Planck/release_3/"
            "ancillary-data/cosmoparams/COM_PowerSpect_CMB-TT-binned_R3.01.txt"
        ),
        kind="txt",
        tier="lite",
        description="Planck 2018 binned C_l^TT for Λ calibration and null spectra.",
        mission="Planck",
        refresh_hours=24.0 * 30,
    ),
    "planck_lcdm_baseline": DataProduct(
        id="planck_lcdm_baseline",
        name="Planck DR3 ΛCDM baseline (reference cosmology)",
        url=(
            "https://irsa.ipac.caltech.edu/data/Planck/release_3/ancillary-data/cosmoparams/"
            "COM_PowerSpect_CMB-base-plikHM-TTTEEE-lowl-lowE-lensing-minimum-theory_R3.01.txt"
        ),
        kind="txt",
        tier="lite",
        description="Planck 2018 baseline theory C_l; anchors ΛCDM landscape calibration.",
        mission="Planck",
        refresh_hours=24.0 * 30,
        filename="planck_lcdm_baseline_theory_cl.txt",
    ),
    "wmap_k_band": DataProduct(
        id="wmap_k_band",
        name="WMAP 9yr Ka-band smoothed IQU map",
        url=(
            "https://lambda.gsfc.nasa.gov/data/map/dr5/skymaps/9yr/smoothed/"
            "wmap_band_smth_iqumap_r9_9yr_K_v5.fits"
        ),
        kind="fits",
        tier="standard",
        description="~100 MB HEALPix map — default real-sky RBLE scan target.",
        mission="WMAP",
        refresh_hours=24.0 * 365,
        filename="wmap_9yr_k_band.fits",
    ),
    "planck_smica_cmb": DataProduct(
        id="planck_smica_cmb",
        name="Planck DR3 SMICA CMB IQU map (2048, no SZ)",
        url=(
            "https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/"
            "maps/component-maps/cmb/COM_CMB_IQU-smica-nosz_2048_R3.00_full.fits"
        ),
        kind="fits",
        tier="heavy",
        description="~384 MB gold-standard CMB component map for production scans.",
        mission="Planck",
        refresh_hours=24.0 * 365,
        filename="planck_smica_cmb_2048.fits",
    ),
    "planck_int_mask": DataProduct(
        id="planck_int_mask",
        name="Planck DR3 intensity confidence mask",
        url=(
            "https://irsa.ipac.caltech.edu/data/Planck/release_3/ancillary-data/masks/"
            "COM_Mask_CMB-common-Mask-Int_2048_R3.00.fits"
        ),
        kind="fits",
        tier="standard",
        description="Galactic plane / point-source mask for clean-sky RBLE scoring.",
        mission="Planck",
        refresh_hours=24.0 * 365,
        filename="planck_cmb_int_mask.fits",
    ),
    "wmap_tt_power": DataProduct(
        id="wmap_tt_power",
        name="WMAP 9yr binned TT power spectrum (lite)",
        url=(
            "https://lambda.gsfc.nasa.gov/data/map/dr5/dcp/spectra/"
            "wmap_binned_tt_spectrum_9yr_v5.txt"
        ),
        kind="txt",
        tier="lite",
        description="WMAP DR5 binned C_l^TT for cross-check against Planck Λ calibration.",
        mission="WMAP",
        refresh_hours=24.0 * 365,
        filename="wmap_binned_tt_spectrum_9yr_v5.txt",
    ),
    "camb_lcdm_cl": DataProduct(
        id="camb_lcdm_cl",
        name="Planck 2018 CAMB ΛCDM theory C_l (TT)",
        url=(
            "https://irsa.ipac.caltech.edu/data/Planck/release_3/ancillary-data/cosmoparams/"
            "COM_PowerSpect_CMB-base-plikHM-TTTEEE-lowl-lowE-lensing-minimum-theory_R3.01.txt"
        ),
        kind="txt",
        tier="lite",
        description="CAMB-generated ΛCDM TT theory spectrum for null-model calibration.",
        mission="Planck",
        refresh_hours=24.0 * 30,
        filename="camb_lcdm_cl_theory.txt",
    ),
    "sdss_bao_ladder": DataProduct(
        id="sdss_bao_ladder",
        name="SDSS spectroscopic redshift ladder (SkyServer JSON)",
        url=(
            "https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
            "?format=json&cmd=SELECT+TOP+20+z,bestClass+FROM+SpecObj+WHERE+z+BETWEEN+0.15+AND+0.8"
            "+AND+bestClass%3D%27GALAXY%27+ORDER+BY+z"
        ),
        kind="json",
        tier="lite",
        description="SDSS public JSON API sample for BAO distance-ladder cross-checks.",
        mission="SDSS",
        refresh_hours=24.0 * 7,
        filename="sdss_bao_ladder.json",
    ),
    "nasa_exoplanet_ps": DataProduct(
        id="nasa_exoplanet_ps",
        name="NASA Exoplanet Archive confirmed planets (planetary systems table)",
        url=(
            "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+pl_name,hostname,"
            "ra,dec,pl_orbper,pl_rade,pl_bmassj,st_teff,pl_eqt,pl_insol,disc_year,discoverymethod"
            "+from+ps+where+default_flag%3D1&format=csv"
        ),
        kind="csv",
        tier="lite",
        description="Real sky positions (RA/Dec) of all confirmed exoplanets — world-atlas scan target.",
        mission="NASA",
        refresh_hours=24.0 * 7,
        filename="nasa_exoplanet_ps.csv",
    ),
}

# GWOSC is API-driven (not a static file) — see sources/gwosc.py
GWOSC_CATALOG_URL = "https://gwosc.org/api/v2/catalogs/GWTC/events?format=json"
GWOSC_EVENTS_PRODUCT_ID = "gwtc_events"
GWOSC_EVENT_DETAIL = "https://gwosc.org/api/v2/events/{name}"


def gwosc_event_detail_url(event_name: str) -> str:
    """Build GWOSC API v2 URL for a single event summary."""
    return GWOSC_EVENT_DETAIL.format(name=event_name)


def list_products(tier: ProductTier | None = None) -> list[DataProduct]:
    products = list(CATALOG.values())
    if tier is not None:
        products = [p for p in products if p.tier == tier]
    return products


def get_product(product_id: str) -> DataProduct:
    if product_id not in CATALOG:
        raise KeyError(f"Unknown data product: {product_id!r}. Available: {list(CATALOG)}")
    return CATALOG[product_id]


LITE_PRODUCT_IDS: tuple[str, ...] = tuple(p.id for p in list_products("lite"))
STANDARD_FETCH_IDS: tuple[str, ...] = ("planck_cmb_tt_power", "planck_lcdm_baseline", "wmap_k_band")
