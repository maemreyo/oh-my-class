from __future__ import annotations

from packages.agents.teaching_pack.artifact_fanout import coordinate_artifact_fanout


def _artifact(artifact_type: str, generation_id: str) -> dict[str, object]:
    return {
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "artifact_generation_id": generation_id,
        "theme": "default",
        "title": f"{artifact_type.title()} Artifact {generation_id}",
        "sections": [{"title": "Intro", "content": "Use unit fractions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


def _workflow_state(artifact_type: str, generation_id: str) -> dict[str, object]:
    return {
        "workflow_id": f"{generation_id}:{artifact_type}",
        "artifact_generation_id": generation_id,
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "status": "passed",
    }


def test_checkpoint_resume_ignores_stale_chunks_and_deduplicates_successful_branches() -> None:
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
        "artifact_chunks": [
            _artifact("lesson", stale_generation),
            _artifact("lesson", current_generation),
            _artifact("quiz", current_generation),
            _artifact("quiz", current_generation),
        ],
        "artifact_workflow_states": [
            _workflow_state("lesson", stale_generation),
            _workflow_state("lesson", current_generation),
            _workflow_state("quiz", current_generation),
            _workflow_state("quiz", current_generation),
        ],
    })

    assert update["artifact_fanout_complete"] is True
    assert [artifact["artifact_type"] for artifact in update["artifacts"]] == ["lesson", "quiz"]
    assert [artifact["artifact_generation_id"] for artifact in update["artifacts"]] == [
        current_generation,
        current_generation,
    ]
