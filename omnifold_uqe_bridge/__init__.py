"""Optional bridge to deepiri-uqe for ER=EPR entanglement layers."""

from omnifold_uqe_bridge.entanglement import cross_branch_gradient
from omnifold_uqe_bridge.er_epr_coupling import map_density_to_conductance

__all__ = ["cross_branch_gradient", "map_density_to_conductance"]
