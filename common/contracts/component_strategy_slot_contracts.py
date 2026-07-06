from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SlotContractModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class StrategyDeliveryMode(StrEnum):
    IN_CLASS = "in_class"
    HOMEWORK = "homework"
    BLENDED = "blended"
    PRINTABLE_TAKEHOME = "printable_takehome"


class StrategyAssessmentIntent(StrEnum):
    NONE = "none"
    FORMATIVE = "formative"
    SUMMATIVE = "summative"
    EXAM_PREP = "exam_prep"
    DIAGNOSTIC = "diagnostic"


class StrategyScoringMode(StrEnum):
    AUTO_GRADABLE = "auto_gradable"
    TEACHER_GRADED = "teacher_graded"
    DISCUSSION_ONLY = "discussion_only"
    SELF_CHECK = "self_check"


class StrategyFeedbackLevel(StrEnum):
    NONE = "none"
    CORRECTNESS = "correctness"
    RATIONALE = "rationale"
    FULL_EXPLANATION = "full_explanation"


class StrategyLoadLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyDeliveryContext(SlotContractModel):
    mode: StrategyDeliveryMode = StrategyDeliveryMode.IN_CLASS
    inference_reason: str = Field(default="default in-class delivery", min_length=1, max_length=240)
    teacher_override: bool = False


class StrategyScoringIntent(SlotContractModel):
    mode: StrategyScoringMode = StrategyScoringMode.SELF_CHECK
    assessment_intent: StrategyAssessmentIntent = StrategyAssessmentIntent.FORMATIVE
    partial_credit_allowed: bool = False
    rationale_required: bool = True
    feedback_level: StrategyFeedbackLevel = StrategyFeedbackLevel.RATIONALE


class StrategySlotExpansionPolicy(SlotContractModel):
    allowed_supporting_micro_components: tuple[str, ...] = Field(default_factory=tuple)
    max_micro_components: int = Field(default=0, ge=0, le=5)


class MisconceptionTarget(SlotContractModel):
    ref: str = Field(min_length=1, max_length=160)
    source: str = Field(min_length=1, max_length=80)
    confidence: str = Field(min_length=1, max_length=40)
    precedence: int = Field(ge=1, le=10)


class ArtifactScopeRecommendation(SlotContractModel):
    artifact_type: str = Field(min_length=1, max_length=80)
    recommendation: str = Field(min_length=1, max_length=240)
    teacher_visible: bool = True
