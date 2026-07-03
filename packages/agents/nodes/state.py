from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class NodeState(TypedDict, total=False):
    raw_request: str
    teacher_id: str
    class_info: dict[str, Any]
    run_id: str
    artifact_types: list[str]
    theme: str
    artifacts: list[dict[str, Any]]
    export_formats: list[str]
    exported_files: list[dict[str, Any]]
    current_step: int
    tokens_used: int
    cost_usd: float
    research_policy: str
    fail_count: NotRequired[int]
    fail_layer: NotRequired[str | None]
    fail_type: NotRequired[str | None]
    fail_context: NotRequired[dict[str, Any] | None]
    export_ready: NotRequired[bool | None]
