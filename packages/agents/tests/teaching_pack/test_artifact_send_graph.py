from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

from packages.agents.teaching_pack.artifact_fanout import (
    coordinate_artifact_fanout,
    route_after_artifact_workflow,
)
from packages.agents.teaching_pack.graph import build_teaching_pack_graph


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


def _base_state(artifact_types: list[str] | None = None) -> dict[str, object]:
    return {
        "run_id": "run-send",
        "contract": {"topic": "Fractions", "theme": "default"},
        # learning_objectives present -- the Recap specialist (#439) compresses
        # from approved objectives/findings and fails closed without any, unlike
        # the old universal placeholder this fixture predates.
        "lesson_plan": {
            "topic": "Fractions",
            "learning_objectives": [{"description": "Compare equivalent fractions."}],
        },
        "research_brief": {"sources": []},
        "artifact_types": artifact_types or ["lesson", "worksheet", "quiz", "drill", "recap"],
    }


def _completed_state(artifact_type: str, status: str = "passed") -> dict[str, object]:
    return {
        "workflow_id": f"gen-1:{artifact_type}",
        "artifact_generation_id": "gen-1",
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "status": status,
    }


def _reference(artifact_type: str, generation_id: str = "gen-1") -> dict[str, object]:
    return {
        "document_id": f"{generation_id}:{artifact_type}-1",
        "artifact_id": f"{artifact_type}-1",
        "artifact_type": artifact_type,
        "generation_id": generation_id,
        "version": 1,
        "title": f"{artifact_type.title()} Artifact",
    }


def test_rollback_flag_routes_directly_to_render_quality(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", "true")

    route = route_after_artifact_workflow(_base_state())

    assert route == "render_quality"


def test_router_issues_only_current_dependency_wave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    monkeypatch.setenv("TEACHING_PACK_DEFAULT_ARTIFACT_PARALLELISM", "3")
    state = {
        **_base_state(),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 1,
        "artifact_workflow_states": [_completed_state("lesson")],
        "artifact_references": [_reference("lesson")],
    }

    route = route_after_artifact_workflow(state)

    assert not isinstance(route, str)
    assert [send.node for send in route] == ["generate_one_artifact", "generate_one_artifact", "generate_one_artifact"]
    assert [send.arg["artifact_type"] for send in route] == ["worksheet", "quiz", "drill"]


def test_slide_deck_only_request_starts_on_slide_deck_wave(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    state = _base_state(["slide_deck"])

    update = coordinate_artifact_fanout(state)
    route = route_after_artifact_workflow({**state, **update})

    assert update["artifact_wave_index"] == 1
    assert update["artifact_fanout_complete"] is False
    assert not isinstance(route, str)
    assert [send.node for send in route] == ["generate_one_artifact"]
    assert [send.arg["artifact_type"] for send in route] == ["slide_deck"]


def test_fanin_advances_waves_after_current_wave_passes() -> None:
    state = {
        **_base_state(),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 0,
        "artifact_references": [_reference("lesson")],
        "artifact_workflow_states": [_completed_state("lesson")],
    }

    update = coordinate_artifact_fanout(state)

    assert update["artifact_wave_index"] == 1
    assert update["artifact_fanout_complete"] is False
    assert update["artifact_references"] == [_reference("lesson")]


def test_dependency_failure_skips_dependents_and_blocks_next_wave() -> None:
    state = {
        **_base_state(),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 0,
        "artifact_workflow_states": [_completed_state("lesson", "failed")],
    }

    update = coordinate_artifact_fanout(state)

    skipped = update["artifact_workflow_states"]


    assert update["artifact_fanout_complete"] is True
    assert update["artifact_fanout_blocked"] is True
    assert [state["artifact_type"] for state in skipped] == ["worksheet", "quiz", "drill", "recap"]
    assert {state["status"] for state in skipped} == {"skipped"}


def test_reducer_completion_order_does_not_change_final_artifact_order() -> None:
    first = coordinate_artifact_fanout({
        **_base_state(["lesson", "quiz", "worksheet"]),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 1,
        "artifact_references": [
            _reference("quiz"),
            _reference("worksheet"),
            _reference("lesson"),
        ],
        "artifact_workflow_states": [
            _completed_state("quiz"),
            _completed_state("worksheet"),
            _completed_state("lesson"),
        ],
    })
    second = coordinate_artifact_fanout({
        **_base_state(["lesson", "quiz", "worksheet"]),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 1,
        "artifact_references": [
            _reference("lesson"),
            _reference("worksheet"),
            _reference("quiz"),
        ],
        "artifact_workflow_states": [
            _completed_state("lesson"),
            _completed_state("worksheet"),
            _completed_state("quiz"),
        ],
    })

    assert [reference["artifact_type"] for reference in first["artifact_references"]] == ["lesson", "quiz", "worksheet"]
    assert [reference["artifact_type"] for reference in second["artifact_references"]] == ["lesson", "quiz", "worksheet"]


@pytest.mark.anyio
async def test_compiled_graph_rollback_flag_calls_existing_content_creator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    async def fake_content_creator_node(state: dict[str, object]) -> dict[str, object]:
        calls.append(state)
        return {"artifacts": [_artifact("lesson")]}

    monkeypatch.setenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", "true")
    monkeypatch.setattr(
        "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke({
        **_base_state(["lesson"]),
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
        ],
    })

    assert calls[0]["artifact_types"] == ["lesson"]
    assert "artifacts" not in result


@pytest.mark.anyio
async def test_rollback_checkpoint_contains_reference_without_generated_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_content_creator_node(_state: dict[str, object]) -> dict[str, object]:
        return {"artifacts": [_artifact("lesson")]}

    monkeypatch.setenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", "true")
    monkeypatch.setattr(
        "packages.agents.sub_agents.content_creator.nodes.content_creator_node",
        fake_content_creator_node,
    )
    checkpointer = MemorySaver()
    graph = build_teaching_pack_graph(checkpointer=checkpointer, interrupt_before=["render_quality"])
    config = {"configurable": {"thread_id": "run-send-thin-checkpoint"}}

    await graph.ainvoke({
        **_base_state(["lesson"]),
        "run_id": "run-send-thin-checkpoint",
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
        ],
    }, config)

    checkpoint = await checkpointer.aget_tuple(config)

    assert checkpoint is not None
    channel_values = checkpoint.checkpoint["channel_values"]
    assert channel_values["artifact_references"][0]["document_id"] == "run-send-thin-checkpoint:artifact:1:lesson-1"
    assert "artifacts" not in channel_values
    assert "sections" not in str(channel_values)


@pytest.mark.anyio
async def test_compiled_graph_runs_waves_before_render_quality_by_default(
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
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke({
        **_base_state(["lesson", "quiz", "recap"]),
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
        ],
    })

    # "lesson", "quiz", and "recap" all now dispatch to real specialists
    # (specialist_registry.py / #439), not this fake content_creator_node --
    # they must still complete, just without hitting the mock.
    assert calls == []
    assert result["artifact_fanout_complete"] is True
    assert [reference["artifact_type"] for reference in result["artifact_references"]] == ["lesson", "quiz", "recap"]


@pytest.mark.anyio
async def test_compiled_graph_runs_slide_deck_only_before_render_quality(
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
    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fake_content_creator_node,
    )

    graph = build_teaching_pack_graph(interrupt_before=["render_quality"])
    result = await graph.ainvoke({
        **_base_state(["slide_deck"]),
        "contract": {
            "topic": "Food vocabulary",
            "theme": "default",
            "artifact_types": ["slide_deck"],
        },
        "completed_stages": [
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
        ],
    })

    # "slide_deck" is built directly by `_slide_deck_artifact` in
    # generate_one_artifact.py (never routed through content_creator_node).
    assert calls == []
    assert result["artifact_fanout_complete"] is True
    assert [reference["artifact_type"] for reference in result["artifact_references"]] == ["slide_deck"]
