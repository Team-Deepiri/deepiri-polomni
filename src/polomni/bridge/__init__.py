"""Optional bridge to deepiri-uqe for ER=EPR entanglement layers."""

from polomni.bridge.entanglement import cross_branch_gradient
from polomni.bridge.er_epr_coupling import map_density_to_conductance

from polomni.bridge.uqe_adapter import (
    apply_uqe_conductance_to_graph,
    density_matrices_from_branch_weights,
    uqe_bridge_from_simulation,
)

__all__ = [
    "apply_uqe_conductance_to_graph",
    "cross_branch_gradient",
    "density_matrices_from_branch_weights",
    "map_density_to_conductance",
    "uqe_bridge_from_simulation",
]
