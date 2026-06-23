"""Shared contracts package — Pydantic v2 models for the oh-my-class pipeline.

All schema contracts live here. Agents and quality gates reference these models
rather than defining their own. This is the single source of truth for data shapes.
"""

from common.contracts.artifact import ArtifactContent, TeachingPack
from common.contracts.auth import Role, Token, User
from common.contracts.judge_output import JudgeOutput, LayerScore
from common.contracts.lesson_plan import AssessmentCheckpoint, LearningObjective, LessonPlan

__all__ = [
    "LessonPlan",
    "LearningObjective",
    "AssessmentCheckpoint",
    "ArtifactContent",
    "TeachingPack",
    "JudgeOutput",
    "LayerScore",
    "Role",
    "User",
    "Token",
]
