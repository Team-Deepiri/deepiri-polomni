"""Modified Einstein gravity with informational stress."""

from polomni.core.gravity.field_equations import (
    einstein_rhs,
    modified_field_residual,
)
from polomni.core.gravity.information_tensor import (
    information_tensor_N,
    trace_I_squared,
)
from polomni.core.gravity.schwarzschild_choice import schwarzschild_metric_with_choice

__all__ = [
    "einstein_rhs",
    "information_tensor_N",
    "modified_field_residual",
    "schwarzschild_metric_with_choice",
    "trace_I_squared",
]
