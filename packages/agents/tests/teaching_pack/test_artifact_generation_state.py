from __future__ import annotations

from packages.agents.teaching_pack.reducers import (
    current_generation_artifact_references,
    current_generation_workflow_states,
)


def test_current_generation_artifact_references_exclude_stale_values() -> None:
    references = [
        {"document_id": "old-lesson", "generation_id": "gen-old", "artifact_type": "lesson"},
        {"document_id": "current-quiz", "generation_id": "gen-current", "artifact_type": "quiz"},
        {"document_id": "current-recap", "generation_id": "gen-current", "artifact_type": "recap"},
        {"document_id": "missing-generation", "artifact_type": "worksheet"},
    ]

    result = current_generation_artifact_references(references, "gen-current")

    assert result == [references[1], references[2]]


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
    assert current_generation_artifact_references([], "gen-current") == []
    assert current_generation_workflow_states([], "gen-current") == []
