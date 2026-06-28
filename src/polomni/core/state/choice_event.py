"""Choice event record for topological domain bifurcation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ChoiceEvent:
    """Record of an N-way choice bifurcation in district superspace.

    At time ``t_choice``, the domain Ω fractures into ``num_choices`` sub-domains
    via the branching operator:

        Ω  →  { Ω_1, Ω_2, …, Ω_N }

    with Dirac activation δ(t - t_choice) in the RBLE master equation.
    """

    district_id: int
    num_choices: int
    t_choice: float
    parent_id: int | None = None
    branch_log_odds: tuple[float, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.district_id < 0:
            raise ValueError("district_id must be non-negative")
        if self.num_choices < 1:
            raise ValueError("num_choices must be >= 1")
        if self.t_choice < 0.0:
            raise ValueError("t_choice must be non-negative")
        if self.branch_log_odds and len(self.branch_log_odds) != self.num_choices:
            raise ValueError("branch_log_odds length must match num_choices")

    @property
    def information_spike(self) -> float:
        """Logarithmic information spike ln(N) for N-choice events."""
        import math

        return math.log(self.num_choices)
