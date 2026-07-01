from __future__ import annotations

import pytest

from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import JsonObject, TeachingPackState


def _artifact(artifact_type: str, generation_id: str) -> JsonObject:
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


def _rejection_state() -> TeachingPackState:
    state: TeachingPackState = {
        "run_id": "run-send-e2e-scoped",
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "quiz", "recap"],
        "artifact_generation_id": "run-send-e2e-scoped:artifact:1",
        "artifact_generation_revision": 1,
        "artifact_wave_index": 2,
        "artifact_fanout_complete": True,
        "artifacts": [
            _artifact("lesson", "run-send-e2e-scoped:artifact:1"),
            _artifact("quiz", "run-send-e2e-scoped:artifact:1"),
            _artifact("recap", "run-send-e2e-scoped:artifact:1"),
        ],
        "gate_payload": {
            "rejection_type": "scoped",
            "artifact_rejections": [
                {"artifact_id": "quiz-run-send-e2e-scoped:artifact:1", "reason": "Needs revision"},
            ],
        },
        "teacher_approved": False,
        "teacher_decision": "reject",
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
            "artifact_workflow",
            "render_quality",
            "teacher_approval",
        ],
    }
    return state


@pytest.mark.anyio
async def test_scoped_rejection_regenerates_only_rejected_artifact_and_dependents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        artifact_types = state["artifact_types"]
        assert isinstance(artifact_types, list)
        artifact_type = str(artifact_types[0])
        calls.append(artifact_type)
        return {"artifacts": [_artifact(artifact_type, "run-send-e2e-scoped:artifact:2")]}

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke(_rejection_state())

    assert calls == ["quiz", "recap"]
    assert result["artifact_regeneration_scope"] == {
        "mode": "type_scoped",
        "artifact_types": ["quiz", "recap"],
    }
    assert [artifact["artifact_type"] for artifact in result["artifacts"]] == [
        "lesson",
        "quiz",
        "recap",
    ]
    assert [artifact["artifact_generation_id"] for artifact in result["artifacts"]] == [
        "run-send-e2e-scoped:artifact:1",
        "run-send-e2e-scoped:artifact:2",
        "run-send-e2e-scoped:artifact:2",
    ]
