from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.research_brief import (  # noqa: TC001 - Pydantic resolves at runtime
    ArtifactResearchGuidance,
    ResearchBrief,
)
from common.contracts.run_contract import (  # noqa: TC001 - Pydantic resolves at runtime
    JsonObject,
    RunContract,
)

CoreArtifactType = Literal[
    "lesson", "worksheet", "quiz", "drill", "recap", "flashcard_deck", "answer_key", "roadmap",
    "slide_deck", "exit_ticket", "reading_passage", "infographic",
]
ArtifactWorkflowStatus = Literal[
    "queued",
    "running",
    "validating",
    "healing",
    "passed",
    "failed",
    "skipped",
    "escalated",
]
ArtifactCheckStatus = Literal["pending", "passed", "failed", "skipped"]


class ArtifactWorkflowState(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)
    artifact_id: str = Field(min_length=1, max_length=64)
    artifact_type: CoreArtifactType
    status: ArtifactWorkflowStatus
    attempts: int = Field(ge=0)
    contract_revision_id: int = Field(ge=1)
    research_guidance_id: str = Field(min_length=1, max_length=64)
    validation_status: ArtifactCheckStatus = "pending"
    judge_status: ArtifactCheckStatus = "pending"
    snapshot_refs: list[str] = Field(default_factory=list)
    last_error: str | None = Field(default=None, max_length=500)


class ArtifactGenerationInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_type: CoreArtifactType
    lesson_blueprint: JsonObject
    contract: RunContract
    research_brief: ResearchBrief
    research_guidance: ArtifactResearchGuidance
    visual_spec: JsonObject
    dependencies: list[CoreArtifactType] = Field(default_factory=list)
