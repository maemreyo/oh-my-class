"""Shared contracts package — Pydantic v2 models for the oh-my-class pipeline.

All schema contracts live here. Agents and quality gates reference these models
rather than defining their own. This is the single source of truth for data shapes.
"""

from common.contracts.answer_key import AnswerKeyContent, AnswerKeySection, AnswerKeyMetadata
from common.contracts.artifact import ArtifactContent, TeachingPack
from common.contracts.auth import Role, Token, User
from common.contracts.components import ContentComponent
from common.contracts.errors import (
    ErrorCode,
    ErrorResponse,
    PipelineErrorResponse,
    ValidationErrorDetail,
)
from common.contracts.judge_output import JudgeOutput, LayerScore
from common.contracts.lesson_plan import AssessmentCheckpoint, LearningObjective, LessonPlan
from common.contracts.log_context import LogContext
from common.contracts.research_bundle import ResearchBundle, ResearchSource
from common.contracts.roadmap import (
    RoadmapContent,
    RoadmapHero,
    RoadmapSection,
    RoadmapSidebar,
)

__all__ = [
    "ArtifactContent",
    "AnswerKeyContent",
    "AnswerKeyMetadata",
    "AnswerKeySection",
    "AssessmentCheckpoint",
    "ContentComponent",
    "ErrorCode",
    "ErrorResponse",
    "JudgeOutput",
    "LayerScore",
    "LessonPlan",
    "LearningObjective",
    "LogContext",
    "PipelineErrorResponse",
    "ResearchBundle",
    "ResearchSource",
    "RoadmapContent",
    "RoadmapHero",
    "RoadmapSection",
    "RoadmapSidebar",
    "Role",
    "TeachingPack",
    "Token",
    "User",
    "ValidationErrorDetail",
]
