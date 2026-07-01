from __future__ import annotations

import pytest

from packages.agents.teaching_pack.artifact_fanout import (
    coordinate_artifact_fanout,
    route_after_artifact_workflow,
)
from packages.agents.teaching_pack.graph import build_teaching_pack_graph


def _artifact(artifact_type: str, generation_id: str = "gen-1") -> dict[str, object]:
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


def _state() -> dict[str, object]:
    return {
        "run_id": "run-scoped",
        "contract": {"topic": "Fractions", "theme": "default"},
        "lesson_plan": {"topic": "Fractions"},
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap"],
        "artifact_generation_id": "run-scoped:artifact:1",
        "artifact_generation_revision": 1,
        "artifact_wave_index": 2,
        "artifact_fanout_complete": True,
        "artifacts": [
            _artifact("lesson"),
            _artifact("worksheet"),
            _artifact("quiz"),
            _artifact("drill"),
            _artifact("recap"),
        ],
    }


def _workflow_state(artifact_type: str, generation_id: str) -> dict[str, object]:
    return {
        "workflow_id": f"{generation_id}:{artifact_type}",
        "artifact_generation_id": generation_id,
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "status": "passed",
    }


def _scoped_gate(artifact_id: str) -> dict[str, object]:
    return {
        "rejection_type": "scoped",
        "artifact_rejections": [{"artifact_id": artifact_id, "reason": "Needs revision"}],
    }


def test_rejecting_quiz_regenerates_quiz_and_recap_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    initial = {**_state(), "gate_payload": _scoped_gate("quiz-gen-1")}

    started = coordinate_artifact_fanout(initial)
    route = route_after_artifact_workflow(started)

    assert started["artifact_generation_id"] == "run-scoped:artifact:2"
    assert started["artifact_generation_revision"] == 2
    assert started["artifact_regeneration_scope"] == {
        "mode": "type_scoped",
        "artifact_types": ["quiz", "recap"],
    }
    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["quiz"]

    after_quiz = coordinate_artifact_fanout({
        **started,
        "artifact_chunks": [_artifact("quiz", "run-scoped:artifact:2")],
        "artifact_workflow_states": [_workflow_state("quiz", "run-scoped:artifact:2")],
    })
    route = route_after_artifact_workflow(after_quiz)

    assert after_quiz["artifact_wave_index"] == 2
    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["recap"]

    complete = coordinate_artifact_fanout({
        **after_quiz,
        "artifact_chunks": [
            _artifact("quiz", "run-scoped:artifact:2"),
            _artifact("recap", "run-scoped:artifact:2"),
        ],
        "artifact_workflow_states": [
            _workflow_state("quiz", "run-scoped:artifact:2"),
            _workflow_state("recap", "run-scoped:artifact:2"),
        ],
    })

    assert complete["artifact_fanout_complete"] is True
    assert [artifact["artifact_type"] for artifact in complete["artifacts"]] == [
        "lesson",
        "worksheet",
        "drill",
        "quiz",
        "recap",
    ]
    assert [artifact["artifact_generation_id"] for artifact in complete["artifacts"]] == [
        "gen-1",
        "gen-1",
        "gen-1",
        "run-scoped:artifact:2",
        "run-scoped:artifact:2",
    ]


def test_rejecting_lesson_regenerates_all_dependents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    started = coordinate_artifact_fanout({**_state(), "gate_payload": _scoped_gate("lesson-gen-1")})

    route = route_after_artifact_workflow(started)

    assert started["artifact_regeneration_scope"] == {
        "mode": "type_scoped",
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap"],
    }
    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["lesson"]


def test_stale_chunks_from_previous_generation_are_ignored() -> None:
    complete = coordinate_artifact_fanout({
        **_state(),
        "artifact_generation_id": "run-scoped:artifact:2",
        "artifact_generation_revision": 2,
        "artifact_wave_index": 1,
        "artifact_fanout_complete": False,
        "artifact_chunks": [
            _artifact("quiz", "run-scoped:artifact:1"),
            _artifact("quiz", "run-scoped:artifact:2"),
        ],
        "artifact_workflow_states": [
            _workflow_state("quiz", "run-scoped:artifact:1"),
            _workflow_state("quiz", "run-scoped:artifact:2"),
        ],
        "artifact_types": ["quiz"],
    })

    assert complete["artifact_fanout_complete"] is True
    assert [artifact["artifact_generation_id"] for artifact in complete["artifacts"]] == [
        "run-scoped:artifact:2",
    ]


@pytest.mark.anyio
async def test_graph_reenters_artifact_workflow_for_scoped_rejection_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        artifact_types = state["artifact_types"]
        assert isinstance(artifact_types, list)
        artifact_type = str(artifact_types[0])
        calls.append(artifact_type)
        return {"artifacts": [_artifact(artifact_type, "run-scoped:artifact:2")]}

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke({
        **_state(),
        "gate_payload": _scoped_gate("quiz-gen-1"),
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
    })

    assert calls == ["quiz", "recap"]
    assert result["artifact_generation_id"] == "run-scoped:artifact:2"
    assert result["artifact_fanout_complete"] is True
