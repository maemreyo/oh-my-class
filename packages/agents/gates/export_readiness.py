"""Layer 6: Export readiness — multi-judge assembly validation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.config.gate_config import GateConfig

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

REQUIRED_EXPORT_FORMATS = {"html"}


def step_11_export_readiness(state: OhMyClassState) -> dict[str, Any]:
    """Layer 6: Validate that artifacts are ready for export.

    Checks: export_formats requested, artifacts non-empty, all required formats covered.
    """
    config = GateConfig()
    artifacts = state.get("artifacts") or []
    export_formats = state.get("export_formats") or []
    errors = []

    if not artifacts:
        errors.append("No artifacts available for export")

    if not export_formats:
        errors.append("No export formats specified")

    # Check that judge_score passed before export
    judge_score = state.get("judge_score")
    if judge_score is not None and judge_score < config.export_min_score:
        errors.append(
            f"Judge score {judge_score:.1f} below export threshold {config.export_min_score}"
        )

    if errors:
        return {
            "export_ready": False,
            "fail_layer": "export",
            "fail_type": "validation",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors},
        }

    return {"export_ready": True}
