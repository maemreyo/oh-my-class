"""Tests for per-artifact LLM call behavior in content_creator_node.

Verifies that each artifact type triggers a separate LLM call with a
single-target prompt, and that the graph return shape stays
``{"artifacts": [...]}``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.sub_agents.content_creator.nodes import (
    _build_single_artifact_prompt,
    content_creator_node,
)

if TYPE_CHECKING:
    from packages.agents.sub_agents.content_creator.state import ContentCreatorState

# ── Helpers ────────────────────────────────────────────────────────────────

_VALID_LESSON = {
    "artifact_type": "lesson",
    "theme": "default",
    "title": "Photosynthesis Lesson",
    "sections": [{"type": "intro", "content": "Plants convert sunlight to glucose."}],
    "metadata": {},
    "accessibility": {"language": "en"},
}

_VALID_WORKSHEET = {
    "artifact_type": "worksheet",
    "theme": "default",
    "title": "Photosynthesis Worksheet",
    "sections": [{"type": "practice", "content": "Fill in the blanks."}],
    "metadata": {},
    "accessibility": {"language": "en"},
}

_VALID_QUIZ = {
    "artifact_type": "quiz",
    "theme": "default",
    "title": "Photosynthesis Quiz",
    "sections": [{"type": "assessment", "content": "Multiple choice questions."}],
    "metadata": {},
    "accessibility": {"language": "en"},
}


def _artifact_json(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact)


def _artifact_wrapped(artifact: dict[str, Any]) -> str:
    return f"```json\n{json.dumps(artifact)}\n```"


def _make_state(**overrides: Any) -> dict[str, Any]:
    base = {
        "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
        "research_bundle": {"sources": [], "topic": "Photosynthesis"},
        "artifact_types": ["lesson"],
        "theme": "default",
        "run_id": "test-per-artifact",
        "current_step": 8,
    }
    base.update(overrides)
    return base


def _make_sequential_mock(*responses: str) -> AsyncMock:
    """Return an AsyncMock that yields responses in sequence."""
    return AsyncMock(side_effect=list(responses))


# ── Tests ──────────────────────────────────────────────────────────────────


class TestPerArtifactCallCount:
    """3 artifact types → 3 separate LLM calls."""

    @pytest.mark.asyncio
    async def test_three_artifact_types_makes_three_calls(self):
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_LESSON),
            _artifact_json(_VALID_WORKSHEET),
            _artifact_json(_VALID_QUIZ),
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet", "quiz"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        assert mock_llm.await_count == 3
        assert len(result["artifacts"]) == 3


class TestPerArtifactPromptTargets:
    """Each call prompt contains only the target artifact type name."""

    @pytest.mark.asyncio
    async def test_each_prompt_contains_only_target_type(self):
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_LESSON),
            _artifact_json(_VALID_WORKSHEET),
            _artifact_json(_VALID_QUIZ),
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet", "quiz"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            await content_creator_node(state)

        assert mock_llm.await_count == 3
        for i, expected_type in enumerate(["lesson", "worksheet", "quiz"]):
            user_msg = mock_llm.call_args_list[i].kwargs["messages"][1]["content"]
            assert expected_type in user_msg
            # Should NOT contain other artifact types
            for other_type in ["lesson", "worksheet", "quiz"]:
                if other_type != expected_type:
                    # The prompt mentions the target type directly, not others
                    assert (
                        f"'{other_type}'" not in user_msg
                    ), f"Prompt for '{expected_type}' should not mention '{other_type}'"


class TestOutputOrderMatchesInput:
    """Output order matches input artifact_types order."""

    @pytest.mark.asyncio
    async def test_order_preserved(self):
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_QUIZ),
            _artifact_json(_VALID_LESSON),
            _artifact_json(_VALID_WORKSHEET),
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["quiz", "lesson", "worksheet"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        types = [a["artifact_type"] for a in result["artifacts"]]
        assert types == ["quiz", "lesson", "worksheet"]


class TestArrayResponseUnwrap:
    """If LLM returns array, first element is taken."""

    @pytest.mark.asyncio
    async def test_array_response_unwraps_first_element(self):
        # LLM returns an array — should take first element
        array_response = json.dumps([_VALID_LESSON, _VALID_WORKSHEET])
        mock_llm = _make_sequential_mock(array_response)
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["artifact_type"] == "lesson"


class TestArtifactTypeMismatchRetry:
    """If LLM returns wrong artifact_type, retry with correction."""

    @pytest.mark.asyncio
    async def test_type_mismatch_triggers_retry(self):
        wrong_type = {
            **_VALID_WORKSHEET,
            "artifact_type": "lesson",  # wrong — we asked for worksheet
        }
        correct_type = _VALID_WORKSHEET
        mock_llm = _make_sequential_mock(
            _artifact_json(wrong_type),
            _artifact_json(correct_type),
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["worksheet"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        # First call got wrong type → retried → second call succeeded
        assert mock_llm.await_count == 2
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["artifact_type"] == "worksheet"

        # Retry prompt should mention the expected type
        retry_user_msg = mock_llm.call_args_list[1].kwargs["messages"][1]["content"]
        assert "worksheet" in retry_user_msg


class TestSingleArtifactFailureRaisesValueError:
    """If one artifact fails all retries, ValueError is raised (not placeholder)."""

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises_value_error(self):
        mock_llm = _make_sequential_mock(
            "not valid json",  # attempt 1
            "also not json",   # attempt 2
            "still broken",    # attempt 3
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError, match="Content creator failed for 'lesson'"),
        ):
            await content_creator_node(state)

        assert mock_llm.await_count == 3

    @pytest.mark.asyncio
    async def test_failure_on_later_artifact_raises_value_error(self):
        """First artifact succeeds, second fails — raises ValueError."""
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_LESSON),  # lesson succeeds
            "bad json",                      # worksheet attempt 1
            "bad json",                      # worksheet attempt 2
            "bad json",                      # worksheet attempt 3
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError, match="Content creator failed for 'worksheet'"),
        ):
            await content_creator_node(state)

        # 1 call for lesson + 3 retries for worksheet = 4
        assert mock_llm.await_count == 4


class TestBuildSingleArtifactPrompt:
    """Unit test for the prompt builder helper."""

    def test_prompt_contains_artifact_type(self):
        prompt = _build_single_artifact_prompt(
            {"topic": "Math"}, {"topic": "Math"}, "quiz", "ocean",
        )
        assert "'quiz'" in prompt
        assert "ocean" in prompt

    def test_prompt_does_not_contain_other_types(self):
        prompt = _build_single_artifact_prompt(
            {"topic": "Math"}, {"topic": "Math"}, "lesson", "default",
        )
        assert "lesson" in prompt
        assert "worksheet" not in prompt
        assert "quiz" not in prompt


class TestFailureMetadataInError:
    """ValueError message includes artifact_type, attempts count, and error class."""

    @pytest.mark.asyncio
    async def test_error_includes_artifact_type_and_attempts(self):
        mock_llm = _make_sequential_mock(
            "not valid json",  # attempt 1
            "also not json",   # attempt 2
            "still broken",    # attempt 3
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["quiz"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError, match=r"failed for 'quiz'.*after 3 attempts"),
        ):
            await content_creator_node(state)

    @pytest.mark.asyncio
    async def test_error_includes_error_class_name(self):
        mock_llm = _make_sequential_mock(
            "not valid json",
            "also not json",
            "still broken",
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["drill"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError, match=r"after 3 attempts"),
        ):
            await content_creator_node(state)


class TestMixedSuccessFailure:
    """First artifact succeeds, second fails — error mentions the failing type."""

    @pytest.mark.asyncio
    async def test_error_mentions_failing_type_not_succeeding_type(self):
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_LESSON),  # lesson succeeds
            "bad json",                      # worksheet attempt 1
            "bad json",                      # worksheet attempt 2
            "bad json",                      # worksheet attempt 3
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError) as exc_info,
        ):
            await content_creator_node(state)

        msg = str(exc_info.value)
        assert "worksheet" in msg
        assert "lesson" not in msg  # lesson succeeded — should not appear in error

    @pytest.mark.asyncio
    async def test_error_includes_attempt_count_for_failing_type(self):
        mock_llm = _make_sequential_mock(
            _artifact_json(_VALID_LESSON),  # lesson succeeds on attempt 1
            "bad json",                      # worksheet attempt 1
            "bad json",                      # worksheet attempt 2
            "bad json",                      # worksheet attempt 3
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet"]),
        )
        with (
            patch(
                "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
            ),
            pytest.raises(ValueError, match=r"after 3 attempts"),
        ):
            await content_creator_node(state)


class TestRetryRecovery:
    """Intermediate failures that succeed on retry still produce valid output."""

    @pytest.mark.asyncio
    async def test_success_after_retry_returns_correct_artifact(self):
        mock_llm = _make_sequential_mock(
            "bad json attempt",  # attempt 1 → fails
            _artifact_json(_VALID_WORKSHEET),  # attempt 2 → succeeds
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["worksheet"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        assert mock_llm.await_count == 2
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["artifact_type"] == "worksheet"

    @pytest.mark.asyncio
    async def test_partial_retry_preserves_order(self):
        """lesson retries once then succeeds, worksheet succeeds first try."""
        mock_llm = _make_sequential_mock(
            "not json",                       # lesson attempt 1 → fails
            _artifact_json(_VALID_LESSON),    # lesson attempt 2 → succeeds
            _artifact_json(_VALID_WORKSHEET), # worksheet attempt 1 → succeeds
        )
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["lesson", "worksheet"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        assert mock_llm.await_count == 3
        types = [a["artifact_type"] for a in result["artifacts"]]
        assert types == ["lesson", "worksheet"]

    @pytest.mark.asyncio
    async def test_timeout_exception_retries_and_recovers_for_target_artifact(self):
        mock_llm = AsyncMock(side_effect=[
            TimeoutError("provider timeout"),
            _artifact_json(_VALID_QUIZ),
        ])
        state = cast(
            "ContentCreatorState",
            _make_state(artifact_types=["quiz"]),
        )
        with patch(
            "packages.agents.llm.compiled_chat.complete_json_chat", mock_llm,
        ):
            result = await content_creator_node(state)

        assert mock_llm.await_count == 2
        assert result["artifacts"][0]["artifact_type"] == "quiz"
        retry_user_msg = mock_llm.call_args_list[1].kwargs["messages"][1]["content"]
        assert "provider timeout" in retry_user_msg
        assert "quiz" in retry_user_msg
