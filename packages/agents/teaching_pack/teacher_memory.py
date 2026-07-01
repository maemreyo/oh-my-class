"""Per-teacher and per-class memory helpers backed by LangGraph BaseStore.

Provides key-value reads/writes for approval history, vocabulary context,
and difficulty skew. Uses the namespaces already defined in store_namespaces.py.
All reads are absent-safe — missing entries return empty defaults.

This is NOT semantic search. It's plain key-value retrieval by
(teacher_id, subject, grade_band) / (teacher_id) keys.
Semantic index (embedding-based) is agent-interaction/002b (parked).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.teaching_pack.store_namespaces import (
    TEACHER_PREFS_TTL_MINUTES,
    class_knowledge_graph_ns,
    teacher_preferences_ns,
)

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

type JsonObject = dict[str, Any]


# ── class context key ────────────────────────────────────────────────────────

def _class_key(subject: str, grade_band: str) -> str:
    """Stable key for a class context within a teacher's store namespace.

    Uses subject + grade_band as a proxy for class identity until a real
    class_id is added to RunContract.
    """
    return f"{subject}::{grade_band}".lower().replace(" ", "_")


# ── vocabulary / topic context ───────────────────────────────────────────────

def read_class_vocabulary(
    store: BaseStore,
    teacher_id: str,
    subject: str,
    grade_band: str,
) -> dict[str, list[str]]:
    """Return stored vocabulary context for this teacher+class.

    Returns ``{"vocabulary": [...], "topics": [...]}`` or empty lists.
    """
    ns = class_knowledge_graph_ns(teacher_id, _class_key(subject, grade_band))
    result = store.get(ns, "vocabulary_context")
    if result is None:
        return {"vocabulary": [], "topics": []}
    value = result.value
    if not isinstance(value, dict):
        return {"vocabulary": [], "topics": []}
    return {
        "vocabulary": _str_list(value.get("vocabulary")),
        "topics": _str_list(value.get("topics")),
    }


def write_vocabulary(
    store: BaseStore,
    teacher_id: str,
    subject: str,
    grade_band: str,
    topic: str,
    vocabulary: list[str],
) -> None:
    """Append a lesson topic and its key vocabulary to the class context.

    Deduplicates before writing; caps the list at 50 entries each to
    prevent unbounded growth.
    """
    ns = class_knowledge_graph_ns(teacher_id, _class_key(subject, grade_band))
    existing = store.get(ns, "vocabulary_context")
    prior: dict[str, list[str]] = {"vocabulary": [], "topics": []}
    if existing is not None and isinstance(existing.value, dict):
        prior = {
            "vocabulary": _str_list(existing.value.get("vocabulary")),
            "topics": _str_list(existing.value.get("topics")),
        }
    merged_vocab = _dedup_cap(prior["vocabulary"] + vocabulary, 50)
    merged_topics = _dedup_cap(prior["topics"] + [topic], 50)
    store.put(
        ns,
        "vocabulary_context",
        {"vocabulary": merged_vocab, "topics": merged_topics},
        ttl=TEACHER_PREFS_TTL_MINUTES,
    )


# ── approval history / difficulty skew ───────────────────────────────────────

def write_gate_approval(
    store: BaseStore,
    teacher_id: str,
    gate_name: str,
    action: str,
    artifact_types: list[str],
) -> None:
    """Record one gate close event in the teacher's approval history.

    Stores per-gate counts: approved / edited / rejected. Used by the
    adaptive-gate fast-lane (priority-upgrades/005) to compute trust scores.
    """
    ns = teacher_preferences_ns(teacher_id)
    key = f"gate_history::{gate_name}"
    existing = store.get(ns, key)
    counts: dict[str, int] = {"approved": 0, "edited": 0, "rejected": 0}
    if existing is not None and isinstance(existing.value, dict):
        raw = existing.value
        counts["approved"] = int(raw.get("approved", 0))
        counts["edited"] = int(raw.get("edited", 0))
        counts["rejected"] = int(raw.get("rejected", 0))
    if action == "approve":
        counts["approved"] += 1
    elif action in {"edit", "request_edits"}:
        counts["edited"] += 1
    elif action == "reject":
        counts["rejected"] += 1
    store.put(ns, key, {**counts, "last_artifact_types": artifact_types}, ttl=TEACHER_PREFS_TTL_MINUTES)


def read_gate_approval_history(
    store: BaseStore,
    teacher_id: str,
    gate_name: str,
) -> dict[str, int]:
    """Return approval counts for a teacher + gate. Returns zeros if absent."""
    ns = teacher_preferences_ns(teacher_id)
    key = f"gate_history::{gate_name}"
    result = store.get(ns, key)
    if result is None or not isinstance(result.value, dict):
        return {"approved": 0, "edited": 0, "rejected": 0}
    raw = result.value
    return {
        "approved": int(raw.get("approved", 0)),
        "edited": int(raw.get("edited", 0)),
        "rejected": int(raw.get("rejected", 0)),
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _dedup_cap(values: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result[-cap:] if len(result) > cap else result
