"""Frozen study configuration models (pre-registration)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

_DEFAULT_CONFIG = Path("data/studies/p1_holdout/study_config.json")


class StringFilterConfig(BaseModel):
    W0: float = 0.0
    beta: float = 0.15
    modes: list[dict[str, float | int]] = Field(default_factory=list)


class P1StudyConfig(BaseModel):
    """Frozen P1 CMB Radon scar study parameters."""

    study_id: str
    version: str
    registered_at: str
    registered_before_holdout: bool = True
    primary_hypothesis: str = "P1_radon_anisotropic_scar"
    maps: dict[str, str | bool]
    resolution: dict[str, int]
    search: dict[str, float | int | str]
    filters: dict[str, object]
    null_tiers: list[str]
    null_ensemble_size: int = 30
    significance: dict[str, float | bool | str]
    injection_calibration: dict[str, float | int | list[int]]
    code_pins: dict[str, str]


def load_p1_config(path: Path | None = None) -> P1StudyConfig:
    path = path or _DEFAULT_CONFIG
    data = json.loads(path.read_text(encoding="utf-8"))
    return P1StudyConfig.model_validate(data)
