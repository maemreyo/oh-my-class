from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from packages.agents.llm.error_summary import safe_message_summary

if TYPE_CHECKING:
    from common.contracts.artifact_workflow import ArtifactWorkflowState
    from common.contracts.quality import QualityFailureClass
    from common.contracts.run_contract import ArtifactType


@dataclass(frozen=True, slots=True)
class GenerationError(RuntimeError):
    error_type: str
    message: str

    def __str__(self) -> str:
        return f"{self.error_type}: {self.message}"


@dataclass(frozen=True, slots=True)
class UnsupportedArtifactTypeError(ValueError):
    artifact_type: ArtifactType

    def __str__(self) -> str:
        return f"unsupported V2 artifact type: {self.artifact_type}"


def generation_error_summary(exc: GenerationError) -> str:
    return safe_message_summary(str(exc), limit=500)


def quality_error_summary(failure_class: QualityFailureClass) -> str:
    return safe_message_summary(f"quality_gate_failed: {failure_class}", limit=500)


def terminal_generation_failure(state: ArtifactWorkflowState) -> ArtifactWorkflowState:
    return state.model_copy(update={"status": "escalated"})
