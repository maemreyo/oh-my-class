from __future__ import annotations

import pytest

from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import TeachingPackState


def _artifact(artifact_type: str) -> dict[str, object]:
    return {
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "theme": "default",
        "title": f"{artifact_type.title()} Artifact",
        "sections": [{"title": "Intro", "content": "Use unit fractions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


def _start_state() -> TeachingPackState:
    return {
        "run_id": "run-send-e2e-happy",
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "quiz", "recap"],
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
        ],
    }


@pytest.mark.anyio
async def test_graph_generates_complete_pack_before_render_quality_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        artifact_types = state["artifact_types"]
        assert isinstance(artifact_types, list)
        artifact_type = str(artifact_types[0])
        calls.append(artifact_type)
        return {"artifacts": [_artifact(artifact_type)]}

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "3")
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke(_start_state())

    assert calls == ["lesson", "quiz", "recap"]
    assert result["artifact_fanout_complete"] is True
    assert [artifact["artifact_type"] for artifact in result["artifacts"]] == [
        "lesson",
        "quiz",
        "recap",
    ]
    assert {state["status"] for state in result["artifact_workflow_states"]} == {"passed"}
