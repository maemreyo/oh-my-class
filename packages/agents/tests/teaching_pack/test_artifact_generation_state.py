from __future__ import annotations

from packages.agents.teaching_pack.reducers import (
    current_generation_artifact_chunks,
    current_generation_workflow_states,
)


def test_current_generation_artifact_chunks_excludes_stale_values() -> None:
    chunks = [
        {"artifact_id": "lesson-1", "artifact_generation_id": "gen-old", "artifact_type": "lesson"},
        {"artifact_id": "quiz-1", "artifact_generation_id": "gen-current", "artifact_type": "quiz"},
        {"artifact_id": "recap-1", "artifact_generation_id": "gen-current", "artifact_type": "recap"},
        {"artifact_id": "worksheet-1", "artifact_type": "worksheet"},
    ]

    result = current_generation_artifact_chunks(chunks, "gen-current")

    assert result == [chunks[1], chunks[2]]


def test_current_generation_workflow_states_excludes_stale_values() -> None:
    states = [
        {
            "workflow_id": "wf-old",
            "artifact_id": "lesson-1",
            "artifact_generation_id": "gen-old",
            "status": "passed",
        },
        {
            "workflow_id": "wf-current-quiz",
            "artifact_id": "quiz-1",
            "artifact_generation_id": "gen-current",
            "status": "failed",
        },
        {
            "workflow_id": "wf-current-recap",
            "artifact_id": "recap-1",
            "artifact_generation_id": "gen-current",
            "status": "skipped",
        },
    ]

    result = current_generation_workflow_states(states, "gen-current")


    assert result == [states[1], states[2]]


def test_current_generation_filters_return_empty_for_missing_generation() -> None:
    assert current_generation_artifact_chunks([], "gen-current") == []
    assert current_generation_workflow_states([], "gen-current") == []
