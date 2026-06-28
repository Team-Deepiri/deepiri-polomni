"""Radon bubble scan, SO(3) rotation, and graviton vacuum streaming."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
from numpy.typing import NDArray

from omnifold_core.conservation import (
    assert_stream_entropy_closure,
    compute_information_trace,
    stream_flux_integral,
)
from omnifold_core.gravity.information_tensor import information_tensor_N
from omnifold_core.radon.so3_rotation import (
    extract_particle_spectrum,
    rotate_radon_bubble,
)
from omnifold_core.radon.transform_r3 import radon_transform_r3
from omnifold_core.state.stream_packet import StreamPacket


@dataclass
class RadonVacuumPipeline:
    """End-to-end Radon encapsulation → rotation → vacuum stream (RBLE Eq. 5)."""

    district_id: int = 0
    parent_id: int | None = None
    num_choices: int = 1
    horizon_area: float = 4.0 * np.pi
    xi_direction: NDArray[np.floating] = field(
        default_factory=lambda: np.array([0.0, 0.0, 1.0], dtype=np.float64)
    )
    scan_offset_p: float = 0.0
    rotation_angles: tuple[float, float, float] = (0.0, 0.0, 0.0)
    entropy_gradient: NDArray[np.floating] | None = None
    vacuum_coupling: float = 1.0

    def encapsulate_and_scan(
        self,
        psi_field: NDArray[np.floating],
    ) -> NDArray[np.float64]:
        """Radon bubble projection R[Psi](p, xi) on the district field."""
        value = radon_transform_r3(psi_field, self.xi_direction, self.scan_offset_p)
        return np.array([value], dtype=np.float64)

    def rotate_particle_properties(
        self,
        radon_bubble: NDArray[np.floating],
    ) -> NDArray[np.float64]:
        """SO(3) alignment to isolate particle spectrum modes."""
        rotated = rotate_radon_bubble(radon_bubble, self.rotation_angles)
        return extract_particle_spectrum(rotated)

    def stream_to_vacuum(
        self,
        rotated_properties: NDArray[np.floating],
        *,
        enforce_conservation: bool = True,
    ) -> StreamPacket:
        """Flux integral through horizon with conservation closure."""
        phi = np.tanh(rotated_properties) * self.vacuum_coupling
        grad = self.entropy_gradient
        if grad is None:
            grad = np.ones(4, dtype=np.float64)
        i_tensor = information_tensor_N(self.num_choices, grad)
        i_trace = compute_information_trace(i_tensor)

        phi_branch = np.asarray(phi, dtype=np.float64).ravel()
        if phi_branch.size < self.num_choices:
            phi_branch = np.pad(
                phi_branch,
                (0, self.num_choices - phi_branch.size),
                mode="edge",
            )
        elif phi_branch.size > self.num_choices:
            phi_branch = phi_branch[: self.num_choices]

        flux = stream_flux_integral(phi_branch, self.horizon_area)
        if enforce_conservation and flux > 1e-15:
            phi_branch = phi_branch * (i_trace / flux)
            flux = stream_flux_integral(phi_branch, self.horizon_area)

        if enforce_conservation:
            assert_stream_entropy_closure(
                phi_branch,
                i_trace,
                horizon_area=self.horizon_area,
            )

        branch_weights = np.ones(self.num_choices, dtype=np.float64) / self.num_choices

        return StreamPacket(
            district_id=self.district_id,
            parent_id=self.parent_id,
            num_choices=self.num_choices,
            phi_stream=[float(x) for x in phi_branch],
            branch_weights=[float(x) for x in branch_weights],
            information_trace=i_trace,
            timestamp=datetime.now(timezone.utc),
        )

    def run(
        self,
        psi_field: NDArray[np.floating],
    ) -> StreamPacket:
        """Full pipeline: scan → rotate → stream."""
        bubble = self.encapsulate_and_scan(psi_field)
        props = self.rotate_particle_properties(bubble)
        return self.stream_to_vacuum(props)
