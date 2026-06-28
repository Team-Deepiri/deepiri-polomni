"""Pydantic model for Radon-vacuum stream packets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StreamPacket(BaseModel):
    """Multiversal data stream Φ_stream flushed through a graviton vacuum well.

    Encodes the holographic district payload produced by the Radon-Vacuum pipeline:

        Φ_stream = ∬_H (Ψ_rotated ⊗ A_vacuum) · dA

    Fields map to superspace injection and Fokker-Planck diffusion drivers in
  the RBLE loop.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    district_id: int = Field(..., ge=0, description="Source spatial district node id")
    parent_id: int | None = Field(default=None, ge=0, description="Parent district id")
    num_choices: int = Field(..., ge=1, description="Branch count N at the choice event")
    phi_stream: list[float] = Field(
        ...,
        min_length=1,
        description="Vacuum stream amplitudes per branch (length N)",
    )
    information_trace: float = Field(
        ...,
        description="Scalar Tr(I_μν I^μν) closure value carried with the packet",
    )
    timestamp: datetime = Field(default_factory=_utc_now)
    branch_weights: list[float] = Field(
        ...,
        min_length=1,
        description="Normalized branch weights p_k after N-way split",
    )

    @field_validator("phi_stream", "branch_weights", mode="before")
    @classmethod
    def _coerce_sequence(cls, value: Any) -> list[float]:
        arr = np.asarray(value, dtype=float).ravel()
        if arr.size == 0:
            raise ValueError("sequence must be non-empty")
        return [float(x) for x in arr]

    @field_validator("branch_weights")
    @classmethod
    def _validate_weights(cls, weights: list[float]) -> list[float]:
        total = float(sum(weights))
        if total <= 0.0:
            raise ValueError("branch_weights must sum to a positive value")
        return [w / total for w in weights]

    @field_validator("phi_stream")
    @classmethod
    def _validate_phi_matches_choices(
        cls, phi_stream: list[float], info: Any
    ) -> list[float]:
        num_choices = info.data.get("num_choices")
        if num_choices is not None and len(phi_stream) != num_choices:
            raise ValueError("len(phi_stream) must equal num_choices")
        return phi_stream

    @field_validator("branch_weights")
    @classmethod
    def _validate_weights_match_choices(
        cls, branch_weights: list[float], info: Any
    ) -> list[float]:
        num_choices = info.data.get("num_choices")
        if num_choices is not None and len(branch_weights) != num_choices:
            raise ValueError("len(branch_weights) must equal num_choices")
        return branch_weights

    def phi_array(self) -> NDArray[np.floating[Any]]:
        """Return Φ_stream as a numpy vector."""
        return np.asarray(self.phi_stream, dtype=float)

    def weights_array(self) -> NDArray[np.floating[Any]]:
        """Return normalized branch weights as a numpy vector."""
        return np.asarray(self.branch_weights, dtype=float)

    def shannon_entropy(self) -> float:
        """Branch entropy S = -Σ_k p_k log p_k (choice information content)."""
        p = self.weights_array()
        p = np.clip(p, 1e-15, 1.0)
        return float(-np.sum(p * np.log(p)))
