"""Layer 6: Export readiness — multi-judge assembly validation."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.config.gate_config import GateConfig

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState

SUPPORTED_EXPORT_FORMATS = {"html"}
FORMAT_REQUIRED_ARTIFACT_TYPES = {
    "html": {"lesson", "worksheet", "quiz", "drill", "recap", "infographic"},
}


def step_11_export_readiness(state: OhMyClassState) -> dict[str, Any]:
    """Layer 6: Validate that artifacts are ready for export.

    Checks: export_formats requested, artifacts non-empty, requested formats
    are supported, artifact types cover format requirements.
    """
    config = GateConfig()
    artifacts = state.get("artifacts") or []
    export_formats = state.get("export_formats") or []
    errors: list[str] = []

    if not artifacts:
        errors.append("No artifacts available for export")

    if not export_formats:
        errors.append("No export formats specified")

    for fmt in export_formats:
        if fmt not in SUPPORTED_EXPORT_FORMATS:
            errors.append(f"Unsupported export format: {fmt!r}")

    artifact_types = {a.get("artifact_type", "") for a in artifacts}
    for fmt in export_formats:
        required = FORMAT_REQUIRED_ARTIFACT_TYPES.get(fmt, set())
        if required and not artifact_types.intersection(required):
            errors.append(
                f"No artifacts with compatible types for format {fmt!r}"
            )

    judge_score = state.get("judge_score")
    if judge_score is not None and judge_score < config.export_min_score:
        errors.append(
            f"Judge score {judge_score:.1f} below export threshold "
            f"{config.export_min_score}"
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
