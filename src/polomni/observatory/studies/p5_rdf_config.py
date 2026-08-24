"""P5-RDF study — preregistered bubble template + RBLE scar axis test."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STUDY_ID = "P5-RDF"
CONFIG_PATH = Path("data/studies/p5_rdf/study_config.json")


def default_config() -> dict:
    return {
        "study_id": STUDY_ID,
        "title": "Remote dipole/quadrupole bubble template + RBLE scar axis",
        "registered": datetime.now(timezone.utc).isoformat(),
        "observables": [
            "phase_a_rdf_rqf_coherence",
            "phase_b_bubble_template_search",
            "phase_c_lcdm_simulation_null",
            "rble_frozen_scar_axis_template",
        ],
        "data": {
            "cmb_map": "planck_smica_cmb",
            "galaxy_tracer": "iras_pscz",
            "scar_axis_source": "data/reports/multi_survey_scar_consensus.json",
            "scar_axis_method": "wmap_k_only_freeze",
        },
        "gates": {
            "M12_visibility": "phase_b p_shuffle<0.01 AND p_sim<0.01 AND rble_gate",
            "M13_rble_model": "template at frozen scar axis p<0.05 vs isotropic",
            "multiverse_physics": "M12 + template axis within 25° of scar axis",
        },
        "honesty": (
            "Does not claim other universes visible until blind Planck holdout. "
            "RBLE operational proof (M8/M9) is a separate tier."
        ),
    }


def write_study_config(path: Path | None = None) -> Path:
    path = path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_config(), indent=2), encoding="utf-8")
    return path
