from __future__ import annotations

from typing import Any

type JsonObject = dict[str, Any]


def _workflow_state_id(state: JsonObject) -> str:
    return str(state.get("workflow_id") or state.get("artifact_id") or "")


def _workflow_state_sort_key(state: JsonObject) -> tuple[str, str]:
    return (str(state.get("artifact_type", "")), _workflow_state_id(state))


def stable_merge_files(prev: list[str], new: list[str]) -> list[str]:
    """Accumulate exported file paths; deduplicate and sort deterministically."""
    seen: set[str] = set(prev or [])
    merged = list(prev or [])
    for path in new or []:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return sorted(merged)


def stable_merge_workflow_states(
    prev: list[JsonObject],
    new: list[JsonObject],
) -> list[JsonObject]:
    """Accumulate artifact branch statuses by workflow_id or artifact_id.

    This is the status-channel sibling of ``artifact_references``. It is a staging
    reducer for branch progress, not the canonical artifact projection.
    New states overwrite old states for the same workflow/artifact id so
    checkpoint replay is idempotent and branch completion order is irrelevant.
    """
    by_id: dict[str, JsonObject] = {_workflow_state_id(state): state for state in (prev or [])}
    for state in new or []:
        by_id[_workflow_state_id(state)] = state
    return sorted(by_id.values(), key=_workflow_state_sort_key)


def stable_merge_artifact_references(
    prev: list[JsonObject],
    new: list[JsonObject],
) -> list[JsonObject]:
    """Merge checkpoint-safe artifact references by durable document identity."""
    by_document_id = {
        str(reference.get("document_id", "")): reference
        for reference in (prev or [])
    }
    for reference in new or []:
        by_document_id[str(reference.get("document_id", ""))] = reference
    return sorted(
        by_document_id.values(),
        key=lambda reference: (
            str(reference.get("artifact_type", "")),
            str(reference.get("document_id", "")),
        ),
    )


def current_generation_workflow_states(
    workflow_states: list[JsonObject],
    artifact_generation_id: str,
) -> list[JsonObject]:
    return [
        state for state in workflow_states or []
        if str(state.get("artifact_generation_id", "")) == artifact_generation_id
    ]


def current_generation_artifact_references(
    references: list[JsonObject],
    artifact_generation_id: str,
) -> list[JsonObject]:
    """Return only references emitted by the active generation cycle."""
    return stable_merge_artifact_references(
        [],
        [
            reference
            for reference in references or []
            if str(reference.get("generation_id", "")) == artifact_generation_id
        ],
    )
