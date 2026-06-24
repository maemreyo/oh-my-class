"""LangGraph state schema for the oh-my-class pipeline.

Defines the shared state TypedDict that flows through every LangGraph node.
Custom reducers handle list deduplication for artifacts and exported files.

State fields follow AGENTS.md §5 exactly.
"""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict


def merge_artifacts(prev: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicated union preserving insertion order.

    Used as a custom reducer for list fields that may be appended to
    from multiple nodes. Deduplicates by 'id' key if present, else by
    stringified value.

    Args:
        prev: Previous accumulated list.
        new: New items to merge in.

    Returns:
        Deduplicated list preserving insertion order.
    """
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in (prev or []) + (new or []):
        key: str = item if isinstance(item, str) else item.get("id", str(item))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def merge_exported_files(
    prev: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Deduplicated merge for exported file paths."""
    return merge_artifacts(prev, new)


class OhMyClassState(TypedDict):
    """Shared state for the oh-my-class LangGraph pipeline.

    Every node reads from and writes to this state.
    Annotated fields use custom reducers for safe concurrent updates.
    NotRequired fields are populated as the pipeline progresses.
    """

    # ── Input ───────────────────────────────────────────────
    raw_request: str
    teacher_id: str
    class_info: dict[str, Any]
    run_id: str

    # ── Planning ────────────────────────────────────────────
    lesson_plan: NotRequired[dict[str, Any]]
    blueprint_approved: bool
    revision_feedback: NotRequired[str]

    # ── Research ────────────────────────────────────────────
    research_bundle: NotRequired[dict[str, Any]]
    research_policy: str  # "basic" | "standard" | "rigorous"

    # ── Content ─────────────────────────────────────────────
    artifact_types: list[str]
    theme: str
    artifacts: Annotated[list[dict[str, Any]], merge_artifacts]

    # ── Quality ─────────────────────────────────────────────
    quality_scores: NotRequired[dict[str, Any]]
    quality_passed: bool
    teacher_approved: bool
    revision_count: int

    # ── HITL Gate ───────────────────────────────────────────
    teacher_decision: NotRequired[str]   # "approve" | "reject" | "edit"
    gate_payload: NotRequired[dict[str, Any]]   # data shown to teacher at gate

    # ── Error ───────────────────────────────────────────────
    error: NotRequired[str]   # set by any node on unrecoverable failure

    # ── Export ──────────────────────────────────────────────
    export_formats: list[str]  # ["html", "gift", "h5p"]
    exported_files: Annotated[list[dict[str, Any]], merge_exported_files]

    # ── Metadata ────────────────────────────────────────────
    current_step: int  # 1–13
    tokens_used: int
    cost_usd: float
