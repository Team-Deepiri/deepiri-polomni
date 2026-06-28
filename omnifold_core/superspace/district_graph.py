"""District graph for RBLE superspace sector branching (RBLE Eq. 6–7)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import networkx as nx
import numpy as np
from numpy.typing import NDArray

from omnifold_core.state.stream_packet import StreamPacket


def _as_float_array(value: NDArray[np.floating] | list[float] | tuple[float, ...]) -> NDArray[np.floating]:
    return np.asarray(value, dtype=float)


class DistrictGraph:
    """Directed graph of spatial districts connected by graviton portal edges.

    Nodes store district mass, local gravity law constants, coordinates, and
    vacuum energy ``Λ``. Edges encode black-hole portal locations and ER=EPR
  conductance ``G_ij`` between parent and child sectors spawned at choice events.

    At a choice bifurcation the parent sector ``i`` spawns ``N`` children; each
    child inherits a mutated ``law_of_gravity`` and an edge annotated with
    ``black_hole_at`` set to the parent's coordinate (RBLE graviton-well portal).
    """

    def __init__(self, gravity_mutation_strength: float = 0.05) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._next_id: int = 0
        self.gravity_mutation_strength = float(gravity_mutation_strength)

    def add_district(
        self,
        mass: float,
        law_of_gravity: NDArray[np.floating] | list[float],
        coordinate: NDArray[np.floating] | list[float],
        lambda_vacuum: float,
    ) -> int:
        """Register a district node and return its integer sector id.

        Parameters
        ----------
        mass:
            Effective district mass parameter ``M_d`` in the Hamiltonian sector.
        law_of_gravity:
            Local gravitational law constants (e.g. Newton ``G``, ``Λ`` projection).
        coordinate:
            Spatial coordinate ``x_d`` where portal edges anchor black holes.
        lambda_vacuum:
            Vacuum energy density ``Λ_d`` from the string landscape sector.
        """
        district_id = self._next_id
        self._next_id += 1
        self.graph.add_node(
            district_id,
            mass=float(mass),
            law_of_gravity=_as_float_array(law_of_gravity),
            coordinate=_as_float_array(coordinate),
            lambda_vacuum=float(lambda_vacuum),
        )
        return district_id

    def trigger_choice_event(self, parent_sector: int, num_choices: int) -> list[StreamPacket]:
        """Spawn ``num_choices`` child districts and emit vacuum stream packets.

        Implements the superspace branching rule from RBLE Eq. (6):

            𝒞_i → {𝒞_{i,k}}_{k=1}^{N},   g_{μν}^{(k)} = g_{μν}^{(i)} + δg_k

        Each child receives a gravity-law mutation ``δg_k`` and a directed edge
        from the parent with ``black_hole_at = x_parent``.

        Returns
        -------
        list[StreamPacket]
            One packet per branch with ``phi_stream`` flux and normalized
            ``branch_weights`` summing to unity.
        """
        if parent_sector not in self.graph:
            raise KeyError(f"parent sector {parent_sector} is not in the district graph")
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")

        parent = self.graph.nodes[parent_sector]
        parent_gravity = np.asarray(parent["law_of_gravity"], dtype=float)
        parent_coord = np.asarray(parent["coordinate"], dtype=float)
        parent_mass = float(parent["mass"])
        parent_lambda = float(parent["lambda_vacuum"])

        log_odds = np.linspace(-0.5, 0.5, num_choices)
        branch_weights = _softmax(log_odds)
        phi_stream = _compute_phi_stream(
            mass=parent_mass,
            lambda_vacuum=parent_lambda,
            coordinate=parent_coord,
            branch_weights=branch_weights,
        )

        packets: list[StreamPacket] = []
        for k in range(num_choices):
            mutation = (k + 1) / num_choices * self.gravity_mutation_strength
            mutated_gravity = parent_gravity * (1.0 + mutation)

            child_id = self._next_id
            self._next_id += 1
            self.graph.add_node(
                child_id,
                mass=parent_mass,
                law_of_gravity=mutated_gravity.copy(),
                coordinate=parent_coord.copy(),
                lambda_vacuum=parent_lambda,
            )
            self.graph.add_edge(
                parent_sector,
                child_id,
                black_hole_at=parent_coord.copy(),
                conductance=float(branch_weights[k]),
            )

            information_trace = float(np.sum(mutated_gravity**2) * parent_mass)

            packets.append(
                StreamPacket(
                    district_id=child_id,
                    parent_id=parent_sector,
                    num_choices=num_choices,
                    phi_stream=phi_stream.tolist(),
                    information_trace=information_trace,
                    timestamp=datetime.now(timezone.utc),
                    branch_weights=[float(w) for w in branch_weights],
                    metadata={"branch_index": k, "gravity_mutation": float(mutation)},
                )
            )

        return packets

    def get_conductance(self, i: int, j: int) -> float:
        """Return ER=EPR conductance ``G_ij`` on directed edge ``i → j``."""
        if not self.graph.has_edge(i, j):
            return 0.0
        return float(self.graph.edges[i, j].get("conductance", 0.0))

    def set_conductance(self, i: int, j: int, value: float) -> None:
        """Set conductance ``G_ij`` on an existing portal edge."""
        if not self.graph.has_edge(i, j):
            raise KeyError(f"edge ({i}, {j}) does not exist")
        self.graph.edges[i, j]["conductance"] = float(value)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the district graph to a JSON-compatible dictionary."""
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            nodes.append(
                {
                    "id": int(node_id),
                    "mass": float(attrs["mass"]),
                    "law_of_gravity": np.asarray(attrs["law_of_gravity"], dtype=float).tolist(),
                    "coordinate": np.asarray(attrs["coordinate"], dtype=float).tolist(),
                    "lambda_vacuum": float(attrs["lambda_vacuum"]),
                }
            )

        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            edge: dict[str, Any] = {
                "source": int(u),
                "target": int(v),
                "conductance": float(attrs.get("conductance", 0.0)),
            }
            if "black_hole_at" in attrs:
                edge["black_hole_at"] = np.asarray(attrs["black_hole_at"], dtype=float).tolist()
            edges.append(edge)

        return {
            "next_id": self._next_id,
            "gravity_mutation_strength": self.gravity_mutation_strength,
            "nodes": nodes,
            "edges": edges,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DistrictGraph:
        """Reconstruct a :class:`DistrictGraph` from :meth:`to_dict` output."""
        graph = cls(gravity_mutation_strength=float(data.get("gravity_mutation_strength", 0.05)))
        graph._next_id = int(data.get("next_id", 0))

        for node in data["nodes"]:
            nid = int(node["id"])
            graph.graph.add_node(
                nid,
                mass=float(node["mass"]),
                law_of_gravity=np.asarray(node["law_of_gravity"], dtype=float),
                coordinate=np.asarray(node["coordinate"], dtype=float),
                lambda_vacuum=float(node["lambda_vacuum"]),
            )
            graph._next_id = max(graph._next_id, nid + 1)

        for edge in data["edges"]:
            attrs: dict[str, Any] = {"conductance": float(edge.get("conductance", 0.0))}
            if "black_hole_at" in edge:
                attrs["black_hole_at"] = np.asarray(edge["black_hole_at"], dtype=float)
            graph.graph.add_edge(int(edge["source"]), int(edge["target"]), **attrs)

        return graph


def _softmax(log_odds: NDArray[np.floating]) -> NDArray[np.floating]:
    """Numerically stable softmax over log-odds amplitudes."""
    shifted = log_odds - np.max(log_odds)
    exp_vals = np.exp(shifted)
    return exp_vals / np.sum(exp_vals)


def _compute_phi_stream(
    mass: float,
    lambda_vacuum: float,
    coordinate: NDArray[np.floating],
    branch_weights: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Construct per-branch vacuum stream amplitudes ``Φ_stream,k`` (RBLE Eq. 5)."""
    coord = np.asarray(coordinate, dtype=float).ravel()
    coord_norm = float(np.linalg.norm(coord)) if coord.size else 0.0
    base_flux = float(mass) + float(lambda_vacuum) + coord_norm
    weights = np.asarray(branch_weights, dtype=float).ravel()
    return base_flux * weights
