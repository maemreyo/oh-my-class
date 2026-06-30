from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GroundingStatus = Literal["grounded", "partial", "ungrounded"]
SchoolStage = Literal["primary", "lower_secondary", "upper_secondary"]


class TopicNorm(BaseModel):
    model_config = ConfigDict(frozen=True)

    curriculum: str = Field(min_length=1, max_length=80)
    locale: str = Field(min_length=2, max_length=16)
    subject: str = Field(min_length=1, max_length=80)
    grade: int = Field(ge=1, le=12)
    topics: tuple[str, ...] = Field(min_length=1)
    lesson_count_min: int = Field(ge=1, le=60)
    lesson_count_max: int = Field(ge=1, le=60)
    session_minutes_min: int = Field(ge=10, le=90)
    session_minutes_max: int = Field(ge=10, le=90)
    session_minutes_default: int = Field(ge=10, le=90)
    bloom_distribution: dict[str, float]
    assessment_distribution: dict[str, float]


class AgeBand(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: SchoolStage
    grade_min: int = Field(ge=1, le=12)
    grade_max: int = Field(ge=1, le=12)
    attention_minutes_min: int = Field(ge=1, le=90)
    attention_minutes_max: int = Field(ge=1, le=90)
    session_minutes_min: int = Field(ge=10, le=90)
    session_minutes_max: int = Field(ge=10, le=90)
    session_minutes_default: int = Field(ge=10, le=90)


class GroundingContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    grounding_status: GroundingStatus
    curriculum: str | None = None
    topic_norm: TopicNorm | None = None
    age_band: AgeBand | None = None
