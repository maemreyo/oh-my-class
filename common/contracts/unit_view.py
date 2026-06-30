from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.lesson_sequence import LessonSequence

UnitViewSchemaVersion = Literal["unit_view.v1"]
UnitAggregateStatus = Literal[
    "awaiting_unit_approval",
    "preparing",
    "generating",
    "in_review",
    "partially_complete",
    "complete",
]
UnitSessionDisplayStatus = Literal["pending", "generating", "in_review", "approved", "failed", "blocked"]
UnitEventType = Literal["unit_aggregate_changed", "unit_session_changed", "unit_coherence_warning"]


class UnitParentMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    parent_run_id: str = Field(min_length=1, max_length=64)
    teacher_id: str = Field(min_length=1, max_length=64)
    topic: str = Field(min_length=1, max_length=200)


class UnitSessionProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    session_id: str = Field(min_length=1, max_length=32)
    child_run_id: str | None = Field(default=None, max_length=64)
    status: UnitSessionDisplayStatus
    progress_percent: int = Field(ge=0, le=100)


class UnitAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    status: UnitAggregateStatus
    total_sessions: int = Field(ge=1, le=20)
    approved_sessions: int = Field(ge=0, le=20)
    failed_sessions: int = Field(ge=0, le=20)


class UnitCoherenceWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)
    session_ids: list[str] = Field(default_factory=list)


class UnitView(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    parent: UnitParentMeta
    sequence: LessonSequence
    sessions: list[UnitSessionProgress] = Field(min_length=1, max_length=20)
    aggregate: UnitAggregate
    coherence_warnings: list[UnitCoherenceWarning] = Field(default_factory=list)
    cursor: int = Field(ge=0)


class UnitSessionStatusEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    session: UnitSessionProgress


class UnitAggregateEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    aggregate: UnitAggregate


class UnitCoherenceWarningEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    warning: UnitCoherenceWarning


class UnitEventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: UnitViewSchemaVersion = "unit_view.v1"
    event_type: UnitEventType
    parent_run_id: str = Field(min_length=1, max_length=64)
    cursor: int = Field(ge=1)
    payload: UnitSessionStatusEvent | UnitAggregateEvent | UnitCoherenceWarningEvent
