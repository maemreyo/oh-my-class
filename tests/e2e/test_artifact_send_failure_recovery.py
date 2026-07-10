from __future__ import annotations

import pytest

from packages.agents.teaching_pack.artifact_status import artifact_statuses_for_teacher
from packages.agents.teaching_pack.graph import build_teaching_pack_graph
from packages.agents.teaching_pack.nodes import TeachingPackState
from packages.agents.teaching_pack.stages import StageEnum


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
            StageEnum.SETUP_CONTRACT,
            StageEnum.TRIAGE,
            StageEnum.PREPLANNING_SEARCH,
            StageEnum.PLANNING_BLUEPRINT,
            StageEnum.POST_BLUEPRINT_RESEARCH,
        ],
    }


@pytest.mark.anyio
async def test_expected_branch_failure_becomes_safe_partial_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_specialist(artifact_type: str):
        def generate(_lesson_plan: dict[str, object], _research_brief: dict[str, object]) -> dict[str, object]:
            if artifact_type == "quiz":
                return {"artifact_type": "quiz", "title": "Invalid quiz"}
            return _artifact(artifact_type)

        return generate

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.get_specialist",
        fake_get_specialist,
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
