from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.teaching_pack.artifact_fanout import (
    coordinate_artifact_fanout,
    route_after_artifact_workflow,
)
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.graph import build_teaching_pack_graph


def _reference(artifact_type: str, generation_id: str = "gen-1") -> dict[str, object]:
    return {
        "document_id": f"{generation_id}:{artifact_type}-1",
        "artifact_id": f"{artifact_type}-{generation_id}",
        "artifact_type": artifact_type,
        "title": f"{artifact_type.title()} Artifact {generation_id}",
        "generation_id": generation_id,
        "version": 1,
    }


def _state() -> dict[str, object]:
    return {
        "run_id": "run-scoped",
        "contract": {"topic": "Fractions", "theme": "default"},
        # learning_objectives present -- the Recap specialist (#439) compresses
        # from approved objectives/findings and fails closed without any, unlike
        # the old universal placeholder this fixture predates.
        "lesson_plan": {
            "topic": "Fractions",
            "learning_objectives": [{"description": "Compare equivalent fractions."}],
        },
        "research_brief": {"sources": []},
        "artifact_types": ["lesson", "worksheet", "quiz", "drill", "recap"],
        "artifact_generation_id": "run-scoped:artifact:1",
        "artifact_generation_revision": 1,
        "artifact_wave_index": 2,
        "artifact_fanout_complete": True,
        "artifact_references": [
            _reference("lesson"),
            _reference("worksheet"),
            _reference("quiz"),
            _reference("drill"),
            _reference("recap"),
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
        "artifact_references": [
            *started["artifact_references"],
            _reference("quiz", "run-scoped:artifact:2"),
        ],
        "artifact_workflow_states": [_workflow_state("quiz", "run-scoped:artifact:2")],
    })
    route = route_after_artifact_workflow(after_quiz)

    assert after_quiz["artifact_wave_index"] == 2
    assert not isinstance(route, str)
    assert [send.arg["artifact_type"] for send in route] == ["recap"]

    complete = coordinate_artifact_fanout({
        **after_quiz,
        "artifact_references": [
            *after_quiz["artifact_references"],
            _reference("quiz", "run-scoped:artifact:2"),
            _reference("recap", "run-scoped:artifact:2"),
        ],
        "artifact_workflow_states": [
            _workflow_state("quiz", "run-scoped:artifact:2"),
            _workflow_state("recap", "run-scoped:artifact:2"),
        ],
    })

    assert complete["artifact_fanout_complete"] is True
    assert [reference["artifact_type"] for reference in complete["artifact_references"]] == [
        "lesson",
        "worksheet",
        "drill",
        "quiz",
        "recap",
    ]
    assert [reference["generation_id"] for reference in complete["artifact_references"]] == [
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
        "artifact_references": [
            _reference("quiz", "run-scoped:artifact:1"),
            _reference("quiz", "run-scoped:artifact:2"),
        ],
        "artifact_workflow_states": [
            _workflow_state("quiz", "run-scoped:artifact:1"),
            _workflow_state("quiz", "run-scoped:artifact:2"),
        ],
        "artifact_types": ["quiz"],
    })

    assert complete["artifact_fanout_complete"] is True
    assert [reference["generation_id"] for reference in complete["artifact_references"]] == [
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
        return {"artifacts": [{
            "artifact_id": f"{artifact_type}-run-scoped:artifact:2",
            "artifact_type": artifact_type,
            "theme": "default",
            "title": f"{artifact_type.title()} Artifact",
            "sections": [{"title": "Intro", "content": "Use unit fractions."}],
            "metadata": {},
            "accessibility": {"language": "en"},
        }]}

    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    content_store = InMemoryArtifactContentStore()
    for artifact_type in ["lesson", "worksheet", "quiz", "drill", "recap"]:
        await content_store.persist(
            "run-scoped",
            "gen-1",
            ArtifactContent(
                artifact_id=f"{artifact_type}-1",
                artifact_type=artifact_type,
                theme="default",
                title=f"{artifact_type.title()} Artifact",
                sections=[{"title": "Intro", "content": "Use unit fractions."}],
                metadata={},
                accessibility={"language": "en"},
            ),
            f"{artifact_type}-1",
        )
    graph = build_teaching_pack_graph(
        content_store=content_store,
        interrupt_before=["render_quality"],
    )
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

    # "recap" is dispatched to the real Recap specialist (#439), not this fake
    # content_creator_node -- it must still complete, just without hitting the mock.
    assert calls == ["quiz"]
    assert result["artifact_generation_id"] == "run-scoped:artifact:2"
    assert result["artifact_fanout_complete"] is True
