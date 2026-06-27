"""Shared contracts package — Pydantic v2 models for the oh-my-class pipeline.

All schema contracts live here. Agents and quality gates reference these models
rather than defining their own. This is the single source of truth for data shapes.
"""

from common.contracts.answer_key import AnswerKeyContent, AnswerKeyMetadata, AnswerKeySection
from common.contracts.artifact import ArtifactContent, TeachingPack
from common.contracts.artifact_workflow import ArtifactGenerationInput, ArtifactWorkflowState
from common.contracts.auth import Role, Token, User
from common.contracts.components import ContentComponent
from common.contracts.diagnostic_report import (
    BloomGap,
    DiagnosticReport,
    KnowledgeGap,
    MisconceptionPattern,
)
from common.contracts.errors import (
    ErrorCode,
    ErrorResponse,
    PipelineErrorResponse,
    ValidationErrorDetail,
)
from common.contracts.judge_output import JudgeOutput, LayerScore
from common.contracts.lesson_plan import AssessmentCheckpoint, LearningObjective, LessonPlan
from common.contracts.log_context import LogContext
from common.contracts.quality import (
    ArtifactQualityReport,
    ExportReadinessReport,
    HealingDecision,
    HealingStrategy,
    QualityFailureClass,
    QualityIssue,
)
from common.contracts.research_brief import (
    ArtifactResearchGuidance,
    EvidenceCitation,
    PrePlanningSearchBrief,
    ResearchBrief,
)
from common.contracts.research_bundle import ResearchBundle, ResearchSource
from common.contracts.roadmap import (
    RoadmapContent,
    RoadmapHero,
    RoadmapSection,
    RoadmapSidebar,
)
from common.contracts.rubric import Rubric, RubricCriterion, RubricLevel, RubricRegistry
from common.contracts.run_contract import ContractRevision, ContractRevisionMeta, RunContract
from common.contracts.student_profile import LearningStyle, PersonalityTrait, StudentProfile
from common.contracts.student_response import StudentAnswerItem, StudentResponse

__all__ = [
    "ArtifactContent",
    "ArtifactGenerationInput",
    "ArtifactResearchGuidance",
    "ArtifactQualityReport",
    "ArtifactWorkflowState",
    "BloomGap",
    "DiagnosticReport",
    "KnowledgeGap",
    "LearningStyle",
    "MisconceptionPattern",
    "PersonalityTrait",
    "StudentAnswerItem",
    "StudentProfile",
    "StudentResponse",
    "AnswerKeyContent",
    "AnswerKeyMetadata",
    "AnswerKeySection",
    "AssessmentCheckpoint",
    "ContentComponent",
    "ContractRevision",
    "ContractRevisionMeta",
    "ErrorCode",
    "ErrorResponse",
    "EvidenceCitation",
    "ExportReadinessReport",
    "HealingDecision",
    "HealingStrategy",
    "JudgeOutput",
    "LayerScore",
    "LessonPlan",
    "LearningObjective",
    "LogContext",
    "PipelineErrorResponse",
    "PrePlanningSearchBrief",
    "QualityFailureClass",
    "QualityIssue",
    "ResearchBrief",
    "ResearchBundle",
    "ResearchSource",
    "RoadmapContent",
    "RoadmapHero",
    "RoadmapSection",
    "RoadmapSidebar",
    "Role",
    "Rubric",
    "RubricCriterion",
    "RubricLevel",
    "RubricRegistry",
    "RunContract",
    "TeachingPack",
    "Token",
    "User",
    "ValidationErrorDetail",
]
