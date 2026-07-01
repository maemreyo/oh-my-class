from __future__ import annotations

import pytest

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
        "lesson_plan": {"topic": "Fractions"},
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
        "artifacts": [{**_artifact("lesson"), "artifact_generation_id": "gen-1"}],
    }

    route = route_after_artifact_workflow(state)

    assert not isinstance(route, str)
    assert [send.node for send in route] == ["generate_one_artifact", "generate_one_artifact", "generate_one_artifact"]
    assert [send.arg["artifact_type"] for send in route] == ["worksheet", "quiz", "drill"]


def test_fanin_advances_waves_after_current_wave_passes() -> None:
    state = {
        **_base_state(),
        "artifact_generation_id": "gen-1",
        "artifact_wave_index": 0,
        "artifact_chunks": [{**_artifact("lesson"), "artifact_generation_id": "gen-1"}],
        "artifact_workflow_states": [_completed_state("lesson")],
    }

    update = coordinate_artifact_fanout(state)

    assert update["artifact_wave_index"] == 1
    assert update["artifact_fanout_complete"] is False
    assert [artifact["artifact_type"] for artifact in update["artifacts"]] == ["lesson"]


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
        "artifact_chunks": [
            {**_artifact("quiz"), "artifact_generation_id": "gen-1"},
            {**_artifact("worksheet"), "artifact_generation_id": "gen-1"},
            {**_artifact("lesson"), "artifact_generation_id": "gen-1"},
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
        "artifact_chunks": [
            {**_artifact("lesson"), "artifact_generation_id": "gen-1"},
            {**_artifact("worksheet"), "artifact_generation_id": "gen-1"},
            {**_artifact("quiz"), "artifact_generation_id": "gen-1"},
        ],
        "artifact_workflow_states": [
            _completed_state("lesson"),
            _completed_state("worksheet"),
            _completed_state("quiz"),
        ],
    })

    assert [artifact["artifact_type"] for artifact in first["artifacts"]] == ["lesson", "quiz", "worksheet"]
    assert [artifact["artifact_type"] for artifact in second["artifacts"]] == ["lesson", "quiz", "worksheet"]


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
    assert result["artifacts"][0]["artifact_type"] == "lesson"


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

    assert calls == ["lesson", "quiz", "recap"]
    assert result["artifact_fanout_complete"] is True
    assert [artifact["artifact_type"] for artifact in result["artifacts"]] == ["lesson", "quiz", "recap"]
