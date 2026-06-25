"""Lesson plan Pydantic models — output contract for the Planner Agent.

Defines the schema for structured lesson plans including learning objectives,
Bloom's taxonomy levels, and assessment checkpoints.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

MethodologyTag = Literal[
    "concept_map",
    "contrastive_pairs",
    "film_based",
    "shy_student_1on1",
    "active_recall",
    "why_wrong_reasoning",
    "timed_quiz",
    "roleplay_script",
]


class MethodologyMetadata(BaseModel):
    tags: list[MethodologyTag] = Field(default_factory=list)
    target_skill_area: str | None = None
    student_profile_notes: str | None = None


class LearningObjective(BaseModel):
    """A single learning objective with Bloom's taxonomy classification."""

    description: str = Field(..., min_length=1, max_length=500)
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
