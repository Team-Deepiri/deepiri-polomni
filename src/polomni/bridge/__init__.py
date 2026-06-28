"""Optional bridge to deepiri-uqe for ER=EPR entanglement layers."""

from polomni.bridge.entanglement import cross_branch_gradient
from polomni.bridge.er_epr_coupling import map_density_to_conductance

__all__ = ["cross_branch_gradient", "map_density_to_conductance"]
