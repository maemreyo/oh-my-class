from __future__ import annotations

import pytest

from packages.agents.teaching_pack.artifact_status import artifact_statuses_for_teacher
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
        "run_id": "run-send-e2e-failure",
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
async def test_expected_branch_failure_becomes_safe_partial_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        artifact_types = state["artifact_types"]
        assert isinstance(artifact_types, list)
        artifact_type = str(artifact_types[0])
        if artifact_type == "quiz":
            return {"artifacts": [{"artifact_type": "quiz", "title": "Invalid quiz"}]}
        return {"artifacts": [_artifact(artifact_type)]}

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke(_start_state())
    statuses = artifact_statuses_for_teacher(result)

    assert result["artifact_fanout_complete"] is True
    assert result["artifact_fanout_blocked"] is True
    assert [status["status"] for status in statuses] == [
        "passed",
        "failed",
        "skipped_due_dependency",
    ]
    assert "Invalid quiz" not in str(statuses)
