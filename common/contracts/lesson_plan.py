"""Lesson plan Pydantic models — output contract for the Planner Agent.

Defines the schema for structured lesson plans including learning objectives,
Bloom's taxonomy levels, and assessment checkpoints.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from common.contracts.inverse_thinking import InverseThinkingPack
from common.contracts.methodology_registry import MethodologyTag


class MethodologyPayloads(BaseModel):
    inverse_thinking: InverseThinkingPack | None = None


class MethodologyMetadata(BaseModel):
    tags: list[MethodologyTag] = Field(default_factory=list)
    target_skill_area: str | None = None
    student_profile_notes: str | None = None
    payloads: MethodologyPayloads = Field(default_factory=MethodologyPayloads)


class LearningObjective(BaseModel):
    """A single learning objective with Bloom's taxonomy classification."""

    description: str = Field(..., min_length=1, max_length=500)
    importance: Literal["core", "supporting", "extension"] | None = None
    assessable: bool | None = None
    assessment_intent: Literal["none", "formative", "summative", "exam_prep", "diagnostic"] | None = None
    bloom_level: str = Field(
        ...,
        pattern=r"^(remember|understand|apply|analyze|evaluate|create)$",
        description="Bloom's taxonomy level",
    )
    assessment_method: str | None = Field(
        default=None,
        max_length=200,
        description="How this objective will be assessed",
    )


class AssessmentCheckpoint(BaseModel):
    """A checkpoint within the lesson for formative assessment."""

    type: str = Field(
        ...,
        description="Checkpoint type, e.g. 'exit_ticket', 'think_pair_share', 'quiz'",
    )
    description: str = Field(..., min_length=1, max_length=500)
    trigger: str | None = Field(
        default=None,
        description="When to trigger this checkpoint, e.g. 'after_phase_2'",
    )


class LessonPlan(BaseModel):
    """Structured lesson plan output from the Planner Agent.

    Follows backward design (UbD) principles and Gagné's 9-event instruction model.
    Bloom levels must cover at least 2 distinct levels.
    """

    topic: str = Field(..., min_length=1, max_length=200)
    grade_level: str = Field(
        ...,
        description="e.g. 'Grade 5', 'Lớp 5'",
    )
    subject: str = Field(
        ...,
        description="e.g. 'math', 'english', 'science'",
    )
    duration_minutes: int = Field(..., ge=10, le=180)
    learning_objectives: list[LearningObjective] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Must cover ≥2 Bloom levels",
    )
    prerequisite_knowledge: list[str] = Field(default_factory=list)
    learning_plan: dict[str, Any] = Field(
        default_factory=dict,
        description="Gagné 9-event phases keyed by phase name",
    )
    assessment_checkpoints: list[AssessmentCheckpoint] = Field(default_factory=list)
    methodology: MethodologyMetadata | None = None
