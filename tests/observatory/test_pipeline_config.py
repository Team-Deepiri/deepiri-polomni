"""Tests for pipeline configuration from environment variables."""

from pathlib import Path

from polomni.observatory.pipeline.config import get_settings, reset_settings_cache


def test_default_settings(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("POLOMNI_DATA_CACHE", raising=False)
    monkeypatch.delenv("POLOMNI_FETCH_TIMEOUT", raising=False)
    monkeypatch.delenv("POLOMNI_GW_POLL_INTERVAL", raising=False)
    reset_settings_cache()

    settings = get_settings()
    assert settings.data_cache == (Path.cwd() / "data" / "cache").resolve()
    assert settings.fetch_timeout == 120.0
    assert settings.gw_poll_interval == 300.0


def test_settings_from_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("POLOMNI_DATA_CACHE", str(tmp_path / "custom-cache"))
    monkeypatch.setenv("POLOMNI_FETCH_TIMEOUT", "45")
    monkeypatch.setenv("POLOMNI_GW_POLL_INTERVAL", "90")
    reset_settings_cache()

    settings = get_settings()
    assert settings.data_cache == (tmp_path / "custom-cache").resolve()
    assert settings.fetch_timeout == 45.0
    assert settings.gw_poll_interval == 90.0
