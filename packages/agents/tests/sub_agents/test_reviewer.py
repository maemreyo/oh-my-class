from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore


def make_judge_output(passed: bool = True, score: float = 8.0) -> JudgeOutput:
	return JudgeOutput(
		overall_score=score,
		layer_scores=[
			LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
			LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
			LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
		],
		critical_issues=[],
		passed=passed,
		rationale="Test rationale",
	)


def _make_llm_response(judge_output: JudgeOutput) -> MagicMock:
	mock = MagicMock()
	mock.choices = [MagicMock()]
	mock.choices[0].message.content = f"```json\n{judge_output.model_dump_json()}\n```"
	return mock


def _make_litellm_mock(return_value: MagicMock) -> MagicMock:
	mock_module = MagicMock()
	mock_module.acompletion = AsyncMock(return_value=return_value)
	return mock_module


class TestQualityReview:
	@pytest.mark.asyncio
	async def test_returns_quality_scores_and_passed(self) -> None:
		from packages.agents.sub_agents.reviewer.agent import quality_review

		good_output = make_judge_output(passed=True, score=8.0)
		mock_litellm = _make_litellm_mock(_make_llm_response(good_output))
		with patch.dict(sys.modules, {"litellm": mock_litellm}):
			result = await quality_review({
				"artifacts": [{"title": "test"}],
				"lesson_plan": {"topic": "Science"},
				"run_id": "run-001",
			})

		assert "quality_scores" in result
		assert "quality_passed" in result
		assert isinstance(result["quality_passed"], bool)

	@pytest.mark.asyncio
	async def test_quality_scores_is_judge_output_dict(self) -> None:
		from packages.agents.sub_agents.reviewer.agent import quality_review

		good_output = make_judge_output(passed=True, score=8.0)
		mock_litellm = _make_litellm_mock(_make_llm_response(good_output))
		with patch.dict(sys.modules, {"litellm": mock_litellm}):
			result = await quality_review({
				"artifacts": [{"title": "test"}],
				"run_id": "run-001",
			})

		scores = result["quality_scores"]
		assert "overall_score" in scores
		assert "passed" in scores
		assert "rationale" in scores

	@pytest.mark.asyncio
	async def test_missing_artifacts_uses_empty_list(self) -> None:
		from packages.agents.sub_agents.reviewer.agent import quality_review

		good_output = make_judge_output(passed=True, score=8.0)
		mock_litellm = _make_litellm_mock(_make_llm_response(good_output))
		with patch.dict(sys.modules, {"litellm": mock_litellm}):
			result = await quality_review({"run_id": "run-001"})

		assert "quality_scores" in result
