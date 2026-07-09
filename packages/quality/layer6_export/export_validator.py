from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# LLM transport protocol — injectable for testability.
LLMTransport = Callable[..., Coroutine[Any, Any, str]]

# Required artifacts per export format
FORMAT_REQUIREMENTS: dict[str, list[str]] = {
    "html": ["lesson"],
    "gift": ["quiz"],
    "h5p": ["quiz", "drill"],
    "qti": ["quiz"],
    "anki_apkg": ["flashcard_deck"],
    "flashcard_tsv": ["flashcard_deck"],
}

INVERSE_THINKING_FORMAT_SUPPORT: dict[str, str] = {
    "html": "supported",
    "gift": "supported",
    "h5p": "unsupported",
    "qti": "supported",
    "google_forms": "lossy",
}


@dataclass
class ExportValidationResult:
    """Result of export readiness validation."""

    passed: bool
    judge_results: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    format_issues: dict[str, list[str]] = field(default_factory=dict)


def check_export_readiness(
    artifacts: list[dict[str, Any]],
    export_formats: list[str],
) -> ExportValidationResult:
    """Deterministic export-readiness: each requested format has its required artifact
    types, and inverse-thinking content is only sent to formats that preserve it.

    This is the real, LLM-free part of Layer-6. The 3-judge majority pass (see
    ``ExportValidator.validate``) is a separate concern tracked with reviewer-004.
    """
    format_issues: dict[str, list[str]] = {}
    artifact_types = {a.get("artifact_type") for a in artifacts}
    inverse_thinking = _contains_inverse_thinking(artifacts)
    for fmt in export_formats:
        missing = [r for r in FORMAT_REQUIREMENTS.get(fmt, []) if r not in artifact_types]
        if missing:
            format_issues[fmt] = [
                f"Missing required artifact type '{r}' for format '{fmt}'" for r in missing
            ]
        if inverse_thinking:
            support = INVERSE_THINKING_FORMAT_SUPPORT.get(fmt, "unsupported")
            if support != "supported":
                format_issues.setdefault(fmt, []).append(
                    f"Inverse-thinking export format '{fmt}' is {support}; required disaster, "
                    "clue, safe-zone, and teacher-rationale semantics cannot be preserved."
                )
    return ExportValidationResult(passed=not format_issues, format_issues=format_issues)


class ExportValidator:
    """Final validation before export packaging.

    Runs 3 independent judge calls with different models.
    2/3 must pass for export to proceed.
    If ≥20% of items fail, stops and asks teacher.
    """

    def __init__(
        self,
        *,
        required_pass_rate: float = 0.67,
        skip_threshold: float = 0.20,
        llm_transport: LLMTransport | None = None,
    ) -> None:
        self.required_pass_rate = required_pass_rate
        self.skip_threshold = skip_threshold
        self._llm_transport = llm_transport

    async def validate(
        self,
        artifacts: list[dict[str, Any]],
        export_formats: list[str],
    ) -> ExportValidationResult:
        det_result = check_export_readiness(artifacts, export_formats)
        if not det_result.passed:
            return det_result

        return await self._run_judge_consensus(artifacts, det_result)

    async def _run_judge_consensus(
        self,
        artifacts: list[dict[str, Any]],
        det_result: ExportValidationResult,
    ) -> ExportValidationResult:
        from packages.agents.config.gate_config import GateConfig
        from packages.quality.layer4_judge.judge_interface import (
            AdaptiveJudge,
            JudgeUnavailableError,
            UnavailableStrategy,
        )

        config = GateConfig()
        transport = self._llm_transport
        strategy = UnavailableStrategy.FAIL_CLOSED
        if transport is None:
            from packages.quality.layer4_judge.judge_transport import (
                default_litellm_transport,
            )
            transport = default_litellm_transport

        judge = AdaptiveJudge(
            llm_transport=transport,
            num_judges=3,
            pass_threshold=config.export_min_score,
            unavailable_strategy=strategy,
        )

        artifact_type = _primary_artifact_type(artifacts)

        try:
            result = await judge.judge(
                artifacts=artifacts,
                artifact_type=artifact_type,
            )
        except JudgeUnavailableError:
            logger.warning("Layer-6 judge unavailable; failing closed")
            return ExportValidationResult(
                passed=False,
                issues=["Layer-6 judge unavailable; export blocked"],
            )

        return ExportValidationResult(
            passed=result.judge_output.passed,
            judge_results=[result.judge_output.model_dump()],
            issues=list(result.judge_output.critical_issues),
            format_issues=det_result.format_issues,
        )


def _contains_inverse_thinking(artifacts: list[dict[str, Any]]) -> bool:
    for artifact in artifacts:
        metadata = artifact.get("metadata")
        methodology = artifact.get("methodology")
        if methodology == "inverse_thinking":
            return True
        if isinstance(metadata, dict) and metadata.get("methodology") == "inverse_thinking":
            return True
    return False


def _primary_artifact_type(artifacts: list[dict[str, Any]]) -> str:
    for artifact in artifacts:
        artifact_type = artifact.get("artifact_type")
        if isinstance(artifact_type, str) and artifact_type:
            return artifact_type
    return "lesson"
