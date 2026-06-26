"""Integration test: pack_scope → visual_engine → research → generate produces artifacts."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from langgraph.types import Command

VALID_PLAN = json.dumps({
    "topic": "Photosynthesis",
    "grade_level": "Grade 5",
    "subject": "science",
    "duration_minutes": 45,
    "learning_objectives": [
        {"description": "Understand photosynthesis", "bloom_level": "understand"},
        {"description": "Apply knowledge", "bloom_level": "apply"},
    ],
})

VALID_BUNDLE = json.dumps({
    "topic": "Photosynthesis",
    "sources": [
        {"title": "S1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
        {"title": "S2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
    ],
})

VALID_ARTIFACTS = json.dumps([{
    "artifact_type": "lesson",
    "theme": "default",
    "title": "Photosynthesis Lesson",
    "sections": [{"title": "Intro", "content": "Plants make food."}],
    "metadata": {},
    "accessibility": {"language": "vi", "alt_texts": {}},
}])


def _routing_complete_json_chat(*, messages: list[dict[str, Any]], **kwargs: Any) -> str:
    user_msg = next(
        (m["content"] for m in messages if m["role"] == "user"), ""
    )
    if "Research topic" in user_msg:
        return VALID_BUNDLE
    if "Generate artifacts" in user_msg:
        return VALID_ARTIFACTS
    return VALID_PLAN


def _initial_state() -> dict[str, Any]:
    return {
        "raw_request": "Teach photosynthesis to Grade 5",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-gen-001",
        "blueprint_approved": False,
        "research_policy": "standard",
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "export_formats": ["html"],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }


@pytest.mark.asyncio
async def test_generate_produces_artifacts():
    mock_llm = AsyncMock(side_effect=_routing_complete_json_chat)
    with pytest.MonkeyPatch.context():
        from unittest.mock import patch

        from packages.agents.graph import build_oh_my_class_graph

        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            graph = build_oh_my_class_graph()
            config = {"configurable": {"thread_id": "test-gen-thread"}}

            state = await graph.ainvoke(_initial_state(), config=config)
            assert state.get("lesson_plan") is not None
            assert state.get("artifact_types") == ["lesson", "worksheet", "quiz"]
            assert state.get("theme") == "default"

            state = await graph.ainvoke(
                Command(resume={"action": "approve"}),
                config=config,
            )

    artifacts = state.get("artifacts", [])
    assert len(artifacts) >= 1
    assert artifacts[0]["artifact_type"] == "lesson"
    assert artifacts[0]["title"] == "Photosynthesis Lesson"
    assert "sections" in artifacts[0]
    assert len(artifacts[0]["sections"]) >= 1


@pytest.mark.asyncio
async def test_pack_scope_and_visual_engine_run_after_approval():
    mock_llm = AsyncMock(side_effect=_routing_complete_json_chat)
    with pytest.MonkeyPatch.context():
        from unittest.mock import patch

        from packages.agents.graph import build_oh_my_class_graph

        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            graph = build_oh_my_class_graph()
            config = {"configurable": {"thread_id": "test-scope-thread"}}

            state = await graph.ainvoke(_initial_state(), config=config)
            state = await graph.ainvoke(
                Command(resume={"action": "approve"}),
                config=config,
            )

    assert state.get("artifact_types") == ["lesson", "worksheet", "quiz"]
    assert state.get("theme") == "default"
    assert state.get("research_bundle") is not None
    assert state["research_bundle"]["topic"] == "Photosynthesis"


@pytest.mark.asyncio
async def test_artifact_has_required_fields():
    from common.contracts.artifact import ArtifactContent

    mock_llm = AsyncMock(side_effect=_routing_complete_json_chat)
    with pytest.MonkeyPatch.context():
        from unittest.mock import patch

        from packages.agents.graph import build_oh_my_class_graph

        with patch("packages.agents.llm.complete_json_chat", mock_llm):
            graph = build_oh_my_class_graph()
            config = {"configurable": {"thread_id": "test-schema-thread"}}

            state = await graph.ainvoke(_initial_state(), config=config)
            state = await graph.ainvoke(
                Command(resume={"action": "approve"}),
                config=config,
            )

    for artifact in state.get("artifacts", []):
        validated = ArtifactContent.model_validate(artifact)
        assert validated.title
        assert len(validated.sections) >= 1
