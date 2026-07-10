from __future__ import annotations

from packages.agents.teaching_pack.artifact_fanout import coordinate_artifact_fanout


def _reference(artifact_type: str, generation_id: str) -> dict[str, object]:
    return {
        "document_id": f"{generation_id}:{artifact_type}-1",
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "title": f"{artifact_type.title()} Artifact {generation_id}",
        "generation_id": generation_id,
        "version": 1,
    }


def _workflow_state(artifact_type: str, generation_id: str) -> dict[str, object]:
    return {
        "workflow_id": f"{generation_id}:{artifact_type}",
        "artifact_generation_id": generation_id,
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "status": "passed",
    }


def test_checkpoint_resume_ignores_stale_references_and_deduplicates_successful_branches() -> None:
    current_generation = "run-send-checkpoint:artifact:2"
    stale_generation = "run-send-checkpoint:artifact:1"

    update = coordinate_artifact_fanout({
        "run_id": "run-send-checkpoint",
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "quiz"],
        "artifact_generation_id": current_generation,
        "artifact_generation_revision": 2,
        "artifact_wave_index": 1,
        "artifact_fanout_complete": False,
        "artifact_references": [
            _reference("lesson", stale_generation),
            _reference("lesson", current_generation),
            _reference("quiz", current_generation),
            _reference("quiz", current_generation),
        ],
        "artifact_workflow_states": [
            _workflow_state("lesson", stale_generation),
            _workflow_state("lesson", current_generation),
            _workflow_state("quiz", current_generation),
            _workflow_state("quiz", current_generation),
        ],
    })

    assert update["artifact_fanout_complete"] is True
    assert [reference["artifact_type"] for reference in update["artifact_references"]] == ["lesson", "quiz"]
    assert [reference["generation_id"] for reference in update["artifact_references"]] == [
        current_generation,
        current_generation,
    ]
