from __future__ import annotations

import pytest

from packages.agents.teaching_pack.nodes import TeachingPackState, make_stage_node
from packages.agents.teaching_pack.stages import TeachingPackStage


@pytest.mark.anyio
async def test_reclaimed_job_skips_completed_stage_without_reexecuting_side_effect(monkeypatch) -> None:
    calls = []

    async def fake_planner_node(state):
        calls.append(state)
        return {"lesson_plan": {"topic": "Duplicate side effect"}}

    monkeypatch.setattr(
        "packages.agents.sub_agents.planner.nodes.planner_node",
        fake_planner_node,
    )
    stage_node = make_stage_node(TeachingPackStage.PLANNING_BLUEPRINT)

    result = await stage_node(TeachingPackState(
        run_id="run-reclaimed",
        completed_stages=["planning_blueprint"],
        lesson_plan={"topic": "Persisted plan"},
    ))

    assert calls == []
    assert result.get("lesson_plan") == {"topic": "Persisted plan"}
