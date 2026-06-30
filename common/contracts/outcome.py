"""Outcome data contracts — student attempts, KC state, delivery records.

Privacy note (PDPD 13/2023): only pseudonym + KC-mastery + score are stored.
Raw student responses and real PII must never appear in these contracts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StudentAttempt(BaseModel):
    schema_version: Literal["student_attempt.v1"] = "student_attempt.v1"
    attempt_id: str  # UUID
    student_pseudonym: str  # hashed identifier, never raw PII
    question_id: str
    kc_ids: list[str]
    correct: bool
    score: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    delivery_id: str


class StudentKCState(BaseModel):
    schema_version: Literal["student_kc_state.v1"] = "student_kc_state.v1"
    state_id: str
    student_pseudonym: str
    kc_id: str
    mastery: float = Field(ge=0.0, le=1.0)
    params: dict[str, float] = Field(default_factory=dict)  # BKT params
    updated_at: datetime


class DeliveryRecord(BaseModel):
    schema_version: Literal["delivery_record.v1"] = "delivery_record.v1"
    delivery_id: str
    run_id: str
    teacher_id: str
    kc_ids: list[str]  # KCs delivered in this pack
    delivered_at: datetime
    class_id: str | None = None
