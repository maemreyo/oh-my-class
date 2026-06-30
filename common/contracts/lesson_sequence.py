from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from common.contracts.methodology_registry import MethodologyTag

SchemaVersion = Literal["lesson_sequence.v1"]
BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
GroundingStatus = Literal["grounded", "partial", "ungrounded"]


class KnowledgeComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: SchemaVersion = "lesson_sequence.v1"
    kc_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=500)


class SessionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: SchemaVersion = "lesson_sequence.v1"
    session_id: str = Field(min_length=1, max_length=32)
    order_index: int = Field(ge=1, le=20)
    child_run_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    sub_topic: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=10, le=90)
    learning_objectives: list[str] = Field(min_length=1, max_length=5)
    bloom_level_primary: BloomLevel
    knowledge_components: list[KnowledgeComponent] = Field(default_factory=list, max_length=4)
    recalled_kc_ids: list[str] = Field(default_factory=list)
    prerequisite_sessions: list[str] = Field(default_factory=list)
    methodology_primary: MethodologyTag
    methodology_secondary: MethodologyTag | None = None


class PrerequisiteEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: SchemaVersion = "lesson_sequence.v1"
    source_kc_id: str = Field(min_length=1, max_length=64)
    target_kc_id: str = Field(min_length=1, max_length=64)
    rationale: str = Field(min_length=1, max_length=300)


class LessonSequence(BaseModel):
    model_config = ConfigDict(frozen=True)
    schema_version: SchemaVersion = "lesson_sequence.v1"
    topic: str = Field(min_length=1, max_length=200)
    grade_level: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=80)
    locale: str = Field(min_length=2, max_length=16)
    total_sessions: int = Field(ge=1, le=20)
    total_duration_minutes: int = Field(ge=10, le=1800)
    sessions: list[SessionPlan] = Field(min_length=1, max_length=20)
    prerequisite_edges: list[PrerequisiteEdge] = Field(default_factory=list)
    grounding_status: GroundingStatus
    confidence: float = Field(ge=0.0, le=1.0)
    open_questions: list[str] = Field(default_factory=list)
    low_confidence_decisions: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_sequence_references(self) -> LessonSequence:
        session_ids = {session.session_id for session in self.sessions}
        for session in self.sessions:
            unknown = set(session.prerequisite_sessions) - session_ids
            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise PydanticCustomError(
                    "unknown_prerequisite_session",
                    "unknown prerequisite session_id(s): {session_ids}",
                    {"session_ids": unknown_list},
                )
        return self
