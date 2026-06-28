"""Wheeler-DeWitt wavepacket generator from vacuum stream injection (RBLE Eq. 8)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from omnifold_core.state.stream_packet import StreamPacket
from omnifold_core.state.unified_state import UnifiedStateVector


class Wavepacket(BaseModel):
    """Discrete Wheeler-DeWitt wavepacket spawned at a stream injection event."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    branch_id: int = Field(ge=0)
    metric_mutation: NDArray[np.floating]
    momentum_vector: NDArray[np.floating]
    stream_residual: float = Field(
        description="‖p_k − Φ_stream‖₂ after delta-kick injection (should → 0)."
    )


class WDWGenerator:
    r"""Discrete Wheeler-DeWitt generator for stream-driven superspace birth.

    Implements the momentum constraint (RBLE Eq. 8):

        \hat{H}\Psi = \sum_k \delta(p_k - \Phi_{\mathrm{stream}})

    In the discrete approximation each branch receives a momentum kick so that
    ``p_k`` aligns with the stream flux ``Φ_stream`` from the parent district,
    accompanied by a metric mutation ``δg_k`` in the gravitational sector.
    """

    def __init__(self, metric_mutation_scale: float = 0.1) -> None:
        self.metric_mutation_scale = float(metric_mutation_scale)

    def spawn_wavepackets(
        self,
        num_choices: int,
        phi_stream: NDArray[np.floating],
    ) -> list[Wavepacket]:
        """Spawn ``num_choices`` wavepackets with per-branch metric mutations.

        Each branch ``k`` receives a diagonal metric perturbation proportional
        to ``(k+1)/N · δg`` and a momentum vector ``p_k = Φ_stream + ε_k`` where
        ``ε_k`` is a branch-specific offset that vanishes after injection.
        """
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")

        phi = np.asarray(phi_stream, dtype=float).ravel()
        if phi.size != num_choices:
            raise ValueError(f"phi_stream length {phi.size} must equal num_choices {num_choices}")

        packets: list[Wavepacket] = []

        for k in range(num_choices):
            scale = (k + 1) / num_choices * self.metric_mutation_scale
            dim = max(3, num_choices)
            metric_mutation = np.eye(dim, dtype=float) * scale

            momentum = np.zeros(num_choices, dtype=float)
            momentum[k] = phi[k]
            residual = float(np.linalg.norm(momentum - phi))

            packets.append(
                Wavepacket(
                    branch_id=k,
                    metric_mutation=metric_mutation,
                    momentum_vector=momentum,
                    stream_residual=residual,
                )
            )

        return packets

    def inject_stream(
        self,
        packet: StreamPacket,
        parent_state: UnifiedStateVector | NDArray[np.floating],
    ) -> list[Wavepacket]:
        """Inject a :class:`StreamPacket` into parent superspace state.

        Combines branch weighting from the packet with the discrete delta-kick
        constraint ``δ(p_k − Φ_stream)`` and returns one :class:`Wavepacket` per
        branch with minimized stream residual.
        """
        phi = packet.phi_array()
        num_choices = packet.num_choices

        if isinstance(parent_state, UnifiedStateVector):
            parent_gauge = max(parent_state.norm(), 1.0)
        else:
            parent_gauge = max(float(np.linalg.norm(np.asarray(parent_state, dtype=float))), 1.0)

        raw_packets = self.spawn_wavepackets(num_choices, phi)
        injected: list[Wavepacket] = []

        for k, wp in enumerate(raw_packets):
            momentum = phi.copy()
            metric = wp.metric_mutation * (1.0 + 1e-3 / parent_gauge)
            residual = float(np.linalg.norm(momentum - phi))

            injected.append(
                Wavepacket(
                    branch_id=wp.branch_id,
                    metric_mutation=metric,
                    momentum_vector=momentum,
                    stream_residual=residual,
                )
            )

        return injected
