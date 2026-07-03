from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class GateState(TypedDict, total=False):
    raw_request: str
    teacher_id: str
    class_info: dict[str, Any]
    run_id: str
    lesson_plan: dict[str, Any]
    blueprint_approved: bool
    revision_feedback: str
    artifact_types: list[str]
    theme: str
    artifacts: list[dict[str, Any]]
    quality_scores: dict[str, Any]
    quality_passed: bool
    teacher_approved: bool
    teacher_decision: str
    gate_payload: dict[str, Any]
    fail_layer: str | None
    fail_count: int
    fail_type: str | None
    fail_context: dict[str, Any] | None
    export_formats: list[str]
    exported_files: list[dict[str, Any]]
    current_step: int
    tokens_used: int
    cost_usd: float
    research_policy: str
    schema_valid: NotRequired[bool | None]
    content_review_passed: NotRequired[bool | None]
    judge_score: NotRequired[float | None]
    export_ready: NotRequired[bool | None]
