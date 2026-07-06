from __future__ import annotations

from enum import StrEnum


class ComponentStrategyMode(StrEnum):
    PROVISIONAL = "provisional"
    FINAL = "final"


class ComponentStrategyStatus(StrEnum):
    PLANNED = "planned"
    PLANNED_WITH_FALLBACK = "planned_with_fallback"
    BLOCKED = "blocked"


class FeedbackEventType(StrEnum):
    PREFER_COMPONENT_FAMILY = "prefer_component_family"
    REJECT_COMPONENT_FAMILY = "reject_component_family"
    PREFER_LEARNING_MOVE = "prefer_learning_move"
    REJECT_LEARNING_MOVE = "reject_learning_move"
    REQUEST_MORE_PRACTICE = "request_more_practice"
    REQUEST_LOWER_TEACHER_LOAD = "request_lower_teacher_load"


class FeedbackSource(StrEnum):
    TEACHER = "teacher"
    SYSTEM = "system"


class ResearchRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class SourceConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MIXED = "mixed"


class PrerequisiteRisk(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    UNMET = "unmet"
    UNKNOWN = "unknown"
    MISSING_SCAFFOLDABLE = "missing_scaffoldable"
    MISSING_BLOCKING = "missing_blocking"


class ComplianceSafety(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    BLOCK = "block"


class ExportProjectionState(StrEnum):
    READY = "ready"
    FALLBACK_REQUIRED = "fallback_required"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"


class RevisionActor(StrEnum):
    SYSTEM = "system"
    TEACHER = "teacher"
    ADMIN = "admin"


class StrategyRevisionMateriality(StrEnum):
    NONE = "none"
    INTERNAL = "internal"
    TEACHER_VISIBLE = "teacher_visible"


class StrategyBlockingIssueCode(StrEnum):
    CORE_OBJECTIVE_UNCOVERED = "core_objective_uncovered"
    NO_ELIGIBLE_COMPONENT = "no_eligible_component"
    FEEDBACK_CONFLICT = "feedback_conflict"
    KNOWLEDGE_DB_STALE = "knowledge_db_stale"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"
    PREREQUISITE_MISSING = "prerequisite_missing"


class StrategyWarningCode(StrEnum):
    FALLBACK_USED = "fallback_used"
    LOW_EVIDENCE_SIGNAL = "low_evidence_signal"
    HIGH_TEACHER_LOAD = "high_teacher_load"
    EXPORT_DEGRADED = "export_degraded"
    OBJECTIVE_DEFERRED = "objective_deferred"
