"""Lab workflow orchestration and profiling."""

from polomni.integration.benchmarks import time_rble_signature

__all__ = ["time_rble_signature"]


def __getattr__(name: str):
    """Lazy imports to avoid circular dependency with inflation.sky_patches."""
    if name == "WorkflowResult":
        from polomni.integration.workflow import WorkflowResult

        return WorkflowResult
    if name == "run_lab_workflow":
        from polomni.integration.workflow import run_lab_workflow

        return run_lab_workflow
    if name == "run_subsystem_suite":
        from polomni.integration.workflow import run_subsystem_suite

        return run_subsystem_suite
    if name == "LoopStepResult":
        from polomni.integration.closed_loop import LoopStepResult

        return LoopStepResult
    if name == "run_closed_loop":
        from polomni.integration.closed_loop import run_closed_loop

        return run_closed_loop
    if name == "run_closed_loop_step":
        from polomni.integration.closed_loop import run_closed_loop_step

        return run_closed_loop_step
    if name == "imprint_cmb_from_packets":
        from polomni.integration.cmb_imprint import imprint_cmb_from_packets

        return imprint_cmb_from_packets
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
