from __future__ import annotations

from typing import Any

type JsonObject = dict[str, Any]


def _artifact_id(artifact: JsonObject) -> str:
    return str(artifact.get("artifact_id") or artifact.get("id") or "")


def _artifact_sort_key(artifact: JsonObject) -> tuple[str, str]:
    return (str(artifact.get("artifact_type", "")), _artifact_id(artifact))


def _workflow_state_id(state: JsonObject) -> str:
    return str(state.get("workflow_id") or state.get("artifact_id") or "")


def _workflow_state_sort_key(state: JsonObject) -> tuple[str, str]:
    return (str(state.get("artifact_type", "")), _workflow_state_id(state))


def stable_merge_artifacts(
    prev: list[JsonObject],
    new: list[JsonObject],
) -> list[JsonObject]:
    """Accumulate artifacts by artifact_id; sort by (type, id) for determinism.

    Each parallel Send branch writes its own artifact(s). This reducer accumulates
    all branches' outputs into a stable, id-keyed list regardless of branch
    completion order. New items overwrite prev items with the same artifact_id.
    """
    by_id: dict[str, JsonObject] = {_artifact_id(a): a for a in (prev or [])}
    for artifact in new or []:
        by_id[_artifact_id(artifact)] = artifact
    return sorted(by_id.values(), key=_artifact_sort_key)


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

    This is the status-channel sibling of ``artifact_chunks``. It is a staging
    reducer for branch progress, not the canonical ``artifacts`` output.
    New states overwrite old states for the same workflow/artifact id so
    checkpoint replay is idempotent and branch completion order is irrelevant.
    """
    by_id: dict[str, JsonObject] = {_workflow_state_id(state): state for state in (prev or [])}
    for state in new or []:
        by_id[_workflow_state_id(state)] = state
    return sorted(by_id.values(), key=_workflow_state_sort_key)


def current_generation_artifact_chunks(
    chunks: list[JsonObject],
    artifact_generation_id: str,
) -> list[JsonObject]:
    current_chunks = [
        chunk for chunk in chunks or []
        if str(chunk.get("artifact_generation_id", "")) == artifact_generation_id
    ]
    return stable_merge_artifacts([], current_chunks)


def current_generation_workflow_states(
    workflow_states: list[JsonObject],
    artifact_generation_id: str,
) -> list[JsonObject]:
    return [
        state for state in workflow_states or []
        if str(state.get("artifact_generation_id", "")) == artifact_generation_id
    ]
