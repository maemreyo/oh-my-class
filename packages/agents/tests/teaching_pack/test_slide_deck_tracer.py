from __future__ import annotations

import pytest

from packages.agents.sub_agents.content_creator.hierarchical import build_hierarchical_artifacts
from packages.agents.teaching_pack.artifact_fanout import route_after_artifact_workflow
from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.stages import StageEnum


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent fractions",
        "grade_level": "Grade 5",
        "learning_objectives": [
            {"description": "Explain why two fractions are equivalent."},
        ],
        "learning_plan": {"present_content": {}, "assess_performance": {}},
    }


def _research_brief() -> dict[str, object]:
    return {
        "sources": [
            {
                "id": "src-fractions-standard",
                "title": "Grade 5 Fractions Standard",
                "citation": "CCSS 5.NF.A",
            },
        ],
    }


@pytest.mark.anyio
async def test_hierarchical_content_creator_returns_slide_deck_artifact() -> None:
    result = await build_hierarchical_artifacts({
        "lesson_plan": _lesson_plan(),
        "research_bundle": _research_brief(),
        "artifact_types": ["slide_deck"],
        "theme": "default",
        "run_id": "run-slide-tracer",
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": [],
    })

    artifact = result["artifacts"][0]

    assert artifact["artifact_type"] == "slide_deck"
    assert artifact["metadata"]["slide_deck_data"]["deck_id"] == "slide-deck-run-slide-tracer"
    assert artifact["sections"][0]["slide_deck"]["slides"][1]["interactions"][0]["teacher_only"]["separation"] == "teacher_only_projection"


@pytest.mark.anyio
async def test_generate_one_artifact_returns_slide_deck_chunk_without_llm() -> None:
    result = await generate_one_artifact({
        "run_id": "run-slide-one",
        "artifact_generation_id": "run-slide-one:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "revision_feedback": "",
        "dependency_artifacts": [],
    })

    chunk = result["artifact_chunks"][0]
    workflow = result["artifact_workflow_states"][0]

    assert chunk["artifact_type"] == "slide_deck"
    assert chunk["metadata"]["slide_deck_data"]["deck_id"] == "slide-deck-run-slide-one"
    assert workflow["artifact_type"] == "slide_deck"
    assert workflow["status"] == "passed"


def test_slide_deck_fanout_runs_after_lesson_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", raising=False)
    state = {
        "run_id": "run-slide-fanout",
        "artifact_generation_id": "run-slide-fanout:artifact:1",
        "artifact_generation_revision": 1,
        "artifact_wave_index": 0,
        "artifact_types": ["lesson", "slide_deck"],
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "contract": {"theme": "default", "artifact_types": ["lesson", "slide_deck"]},
        "artifact_workflow_states": [
            {
                "artifact_generation_id": "run-slide-fanout:artifact:1",
                "artifact_type": "lesson",
                "status": "passed",
            },
        ],
        "artifacts": [{"artifact_type": "lesson", "artifact_id": "lesson-1"}],
    }

    routed = route_after_artifact_workflow({**state, "artifact_wave_index": 1})

    assert not isinstance(routed, str)
    assert len(routed) == 1
    assert routed[0].node == "generate_one_artifact"
    assert routed[0].arg["artifact_type"] == "slide_deck"
    assert routed[0].arg["dependency_artifacts"] == [{"artifact_type": "lesson", "artifact_id": "lesson-1"}]
