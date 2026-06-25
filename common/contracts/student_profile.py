"""StudentProfile Pydantic models — output contract for the Profiler Agent.

Captures the student's learning style, personality traits, goals, and context
so downstream agents (planner, content creator) can personalise their output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LearningStylePrimary = Literal["visual", "auditory", "kinesthetic", "reading"]
TargetExam = Literal["HSA", "IELTS", "TOEIC"]


class PersonalityTrait(BaseModel):
    """A single MBTI-style or pedagogical personality trait."""

    trait: str
    vn_name: str
    teaching_principle: str


class LearningStyle(BaseModel):
    """How the student best absorbs new information."""

    primary: LearningStylePrimary
    media_preference: str | None = None
    format_preference: str | None = None  # "1v1" | "group" | "self-study"


class StudentProfile(BaseModel):
    """Complete learner profile produced by the Profiler Agent."""

    student_id: str
    learning_style: LearningStyle
    personality_traits: list[PersonalityTrait] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    target_score: int | None = None
    target_exam: TargetExam | None = None
    study_duration_months: int = Field(default=6, ge=1, le=24)
    tools: list[str] = Field(default_factory=list)
    raw_context: str = ""
