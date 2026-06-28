"""Tests for frozen P1 study config."""

from pathlib import Path

from polomni.observatory.studies.config import load_p1_config


def test_p1_config_loads() -> None:
    cfg = load_p1_config()
    assert cfg.study_id == "p1_cmb_radon_scar"
    assert cfg.version == "1.0.0"
    assert cfg.registered_before_holdout is True


def test_p1_config_matches_prereg() -> None:
    cfg = load_p1_config()
    assert cfg.maps["calibration_product_id"] == "wmap_k_band"
    assert cfg.maps["holdout_product_id"] == "planck_smica_cmb"
    assert cfg.resolution["search_nside"] == 128
    assert cfg.significance["alpha"] == 0.01
    assert cfg.significance["correction"] == "bonferroni"
    assert len(cfg.null_tiers) == 3


def test_prereg_doc_exists() -> None:
    path = Path("docs/studies/P1_CMB_RADON_SCAR_PREREG.md")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "registered before" in text.lower() or "Registered **before**" in text
