from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.sub_agents.content_creator.nodes import content_creator_node

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState


VALID_ARTIFACT = {
    "artifact_type": "lesson",
    "theme": "default",
    "title": "Equivalent Fractions Lesson",
    "sections": [{"type": "intro", "content": "Equivalent fractions preserve value."}],
    "metadata": {},
    "accessibility": {"language": "vi"},
}


def _large_lesson_plan() -> dict[str, Any]:
    return {
        "topic": "Phân số tương đương",
        "grade_level": "Grade 5",
        "subject": "math",
        "duration_minutes": 60,
        "learning_objectives": [
            {
                "description": "Học sinh xác định phân số tương đương bằng hình ảnh.",
                "bloom_level": "understand",
                "assessment_method": "Bài tập điền vào chỗ trống.",
            },
            {
                "description": "Học sinh tạo phân số tương đương bằng mô hình trực quan.",
                "bloom_level": "apply",
                "assessment_method": "Hoạt động nhóm.",
            },
        ],
        "learning_plan": {
            f"event_{index}": {
                "name": f"Gagné event {index}",
                "title": f"Phase {index}",
                "duration_minutes": index,
                "activities": [
                    "Minh họa bằng thanh phân số tương tác. " * 20,
                    "Học sinh thảo luận và giải thích bằng lời. " * 20,
                ],
            }
            for index in range(1, 10)
        },
        "assessment_checkpoints": [
            {
                "type": "formative",
                "description": "Quan sát học sinh khi dùng mô hình trực quan. " * 30,
                "trigger": "Trong hoạt động nhóm",
            }
        ],
        "methodology": {"tags": ["concept_map", "contrastive_pairs"]},
    }


def _large_research_bundle() -> dict[str, Any]:
    return {
        "topic": "Phân số tương đương",
        "sources": [
            {
                "title": f"Source {index}",
                "url": f"https://example.edu/source-{index}",
                "credibility_score": 0.8,
                "verification_status": "VERIFIED" if index < 3 else "UNCERTAIN",
                "notes": "Long source notes " * 100,
            }
            for index in range(10)
        ],
        "key_findings": [
            "Visual fraction models help students preserve value. " * 30,
            "Contrastive examples reduce numerator-only errors. " * 30,
            "Students should explain equivalence before symbolic shortcuts. " * 30,
        ],
        "cross_references": [{"claim": "Equivalent fractions need same value"}] * 20,
    }


def _state() -> ContentCreatorState:
    return cast(
        "ContentCreatorState",
        {
            "lesson_plan": _large_lesson_plan(),
            "research_bundle": _large_research_bundle(),
            "artifact_types": ["lesson"],
            "theme": "default",
            "run_id": "prompt-size-run",
            "current_step": 8,
        },
    )


@pytest.mark.asyncio
async def test_lesson_only_prompt_stays_under_live_timeout_threshold():
    mock_llm = AsyncMock(return_value=json.dumps([VALID_ARTIFACT]))

    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        await content_creator_node(_state())

    user_msg = mock_llm.call_args.kwargs["messages"][1]["content"]
    assert len(user_msg) < 12000


@pytest.mark.asyncio
async def test_total_llm_messages_stay_under_live_timeout_threshold():
    mock_llm = AsyncMock(return_value=json.dumps([VALID_ARTIFACT]))

    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        await content_creator_node(_state())

    messages = mock_llm.call_args.kwargs["messages"]
    total_chars = sum(len(message["content"]) for message in messages)
    assert total_chars < 25000


@pytest.mark.asyncio
async def test_runtime_prompt_documents_required_component_fields():
    mock_llm = AsyncMock(return_value=json.dumps([VALID_ARTIFACT]))

    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        await content_creator_node(_state())

    system_msg = mock_llm.call_args.kwargs["messages"][0]["content"]
    assert "heading" in system_msg and "level" in system_msg
    assert "paragraph" in system_msg and "text" in system_msg
    assert "callout" in system_msg and "variant" in system_msg
    assert "flow_step" in system_msg and "steps" in system_msg
    assert "phase_timeline" in system_msg and "phases" in system_msg
    assert "table" in system_msg and "columns" in system_msg


@pytest.mark.asyncio
async def test_retry_prompt_preserves_lesson_and_research_context():
    invalid_artifact = {
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Equivalent Fractions Lesson",
        "sections": [
            {
                "type": "concept",
                "title": "Start",
                "components": [{"type": "heading", "text": "Equivalent Fractions"}],
            }
        ],
        "metadata": {},
        "accessibility": {"language": "vi"},
    }
    mock_llm = AsyncMock(side_effect=[json.dumps([invalid_artifact]), json.dumps([VALID_ARTIFACT])])

    with patch("packages.agents.llm.complete_json_chat", mock_llm):
        await content_creator_node(_state())

    retry_user_msg = mock_llm.await_args_list[1].kwargs["messages"][1]["content"]
    assert "Previous validation error" in retry_user_msg
    assert "Lesson Plan Summary" in retry_user_msg
    assert "Research Summary" in retry_user_msg
    assert "Phân số tương đương" in retry_user_msg
    assert len(retry_user_msg) < 15000
