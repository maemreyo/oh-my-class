from __future__ import annotations

import hashlib
import re
from typing import Final, Self

from pydantic import Field

from common.contracts.component_strategy import ComponentStrategyRequest, StrategyModel

PII_DELIVERY_CONTEXT_KEYS: Final = frozenset({"student_names", "student_emails", "individual_scores", "email"})
FINGERPRINT_CONTEXT_KEYS: Final = ("class_context_tags", "cohort_tags", "delivery_mode")
EMAIL_RE: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class StrategyRequestFingerprint(StrategyModel):
    objective_refs: tuple[str, ...]
    subject: str
    grade_band: str
    duration_bucket: str
    artifact_types: tuple[str, ...]
    export_formats: tuple[str, ...]
    locale: str
    class_context_tags: tuple[str, ...] = Field(default_factory=tuple)
    research_signal_digest: str
    teacher_preference_version: str
    outcome_signal_version: str
    knowledge_db_version: str
    scoring_profile_id: str
    selector_version: str
    renderer_capability_checksum: str
    exporter_capability_checksum: str
    cross_run_final_plan_cache_enabled: bool = False

    @classmethod
    def from_request(
        cls,
        request: ComponentStrategyRequest,
        *,
        knowledge_db_version: str,
        scoring_profile_id: str,
        selector_version: str,
        renderer_capability_checksum: str,
        exporter_capability_checksum: str,
    ) -> Self:
        return cls(
            objective_refs=tuple(f"{ref.objective_id}@{ref.objective_revision}" for ref in request.objective_refs),
            subject=request.subject.lower(),
            grade_band=_grade_band(request.grade_level),
            duration_bucket=_duration_bucket(request.duration_minutes),
            artifact_types=tuple(sorted(request.artifact_types)),
            export_formats=tuple(sorted(request.export_formats)),
            locale=request.locale,
            class_context_tags=_class_context_tags(request),
            research_signal_digest=_research_digest(request),
            teacher_preference_version=_teacher_preference_version(request),
            outcome_signal_version="outcome_signals.v1",
            knowledge_db_version=knowledge_db_version,
            scoring_profile_id=scoring_profile_id,
            selector_version=selector_version,
            renderer_capability_checksum=renderer_capability_checksum,
            exporter_capability_checksum=exporter_capability_checksum,
        )


class StrategyDecisionLedger(StrategyModel):
    run_id: str = Field(min_length=1, max_length=80)
    redacted_payload: dict[str, str | int | float | bool]
    contains_strategy_debug_data: bool = True
    retention_ttl_days: int = Field(default=14, ge=1, le=30)
    access_scope: str = "admin_debug_only"

    @classmethod
    def from_debug_payload(cls, run_id: str, payload: dict[str, str | int | float | bool]) -> Self:
        return cls(run_id=run_id, redacted_payload={key: _redact(value) for key, value in payload.items()})


class StrategyObservabilitySummary(StrategyModel):
    status: str = Field(min_length=1, max_length=80)
    knowledge_db_version: str = Field(min_length=1, max_length=80)
    selector_version: str = Field(min_length=1, max_length=80)
    quality_overall: float | None = Field(default=None, ge=0, le=1)
    fallback_reason: str | None = Field(default=None, max_length=120)
    blocking_issue_codes: tuple[str, ...] = Field(default_factory=tuple)
    latency_ms: int | None = Field(default=None, ge=0)
    cache_status: str = Field(default="miss", min_length=1, max_length=40)

    def event_payload(self) -> dict[str, str | int | float | tuple[str, ...] | None]:
        return self.model_dump(mode="json")


def contains_forbidden_delivery_context(keys: set[str]) -> str | None:
    forbidden = keys.intersection(PII_DELIVERY_CONTEXT_KEYS)
    return sorted(forbidden)[0] if forbidden else None


def _grade_band(grade_level: str) -> str:
    digits = "".join(char for char in grade_level if char.isdigit())
    grade = int(digits or "5")
    if grade <= 6:
        return "grade_4_6"
    if grade <= 9:
        return "grade_7_9"
    return "grade_10_12"


def _duration_bucket(minutes: int) -> str:
    lower = (minutes // 15) * 15
    upper = lower + 14
    return f"{lower}_{upper}"


def _class_context_tags(request: ComponentStrategyRequest) -> tuple[str, ...]:
    tags = [str(request.delivery_context[key]) for key in FINGERPRINT_CONTEXT_KEYS if key in request.delivery_context]
    return tuple(sorted(tags))


def _research_digest(request: ComponentStrategyRequest) -> str:
    if request.research_signals is None:
        return "none"
    parts = (
        str(request.research_signals.factual_risk),
        str(request.research_signals.source_confidence),
        str(request.research_signals.prerequisite_risk),
        ",".join(sorted(request.research_signals.evidence_tags)),
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _teacher_preference_version(request: ComponentStrategyRequest) -> str:
    if request.teacher_preferences is None:
        return "teacher_preferences:none"
    facts = sorted(f"{event.event_type}:{event.source}:{event.value}" for event in request.teacher_preferences.feedback_events)
    return hashlib.sha256("|".join(facts).encode()).hexdigest()[:16]


def _redact(value: str | int | float | bool) -> str | int | float | bool:
    if isinstance(value, str):
        return EMAIL_RE.sub("[redacted-email]", value)
    return value
