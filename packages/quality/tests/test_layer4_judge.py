"""Tests for layer4_judge — majority_vote and GEvalScorer."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.quality.layer4_judge.majority_vote import majority_vote

# ── helpers ───────────────────────────────────────────────────────────────────

def make_judge_output(passed: bool = True, score: float = 8.0, critical_issues: list[str] | None = None) -> JudgeOutput:  # noqa: E501
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=critical_issues or [],
        passed=passed,
        rationale="Test rationale",
        teacher_facing_summary="Teacher summary",
    )


def _make_llm_response(judge_output: JudgeOutput) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = f"```json\n{judge_output.model_dump_json()}\n```"
    return mock


def _make_litellm_mock(return_value=None, side_effect=None) -> MagicMock:
    mock_module = MagicMock()
    if side_effect is not None:
        mock_module.acompletion = AsyncMock(side_effect=side_effect)
    else:
        mock_module.acompletion = AsyncMock(return_value=return_value)
    return mock_module


# ── MajorityVote ──────────────────────────────────────────────────────────────

class TestMajorityVote:
    def test_all_pass(self):
        outputs = [make_judge_output(passed=True) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is True

    def test_two_pass_one_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=True),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is True

    def test_one_pass_two_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=False),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is False

    def test_score_below_threshold(self):
        outputs = [make_judge_output(passed=True, score=6.0) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is False
        assert result.overall_score < 7.0

    def test_score_at_threshold_passes(self):
        outputs = [make_judge_output(passed=True, score=7.0) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is True
        assert result.overall_score == pytest.approx(7.0)

    def test_critical_issues_force_fail(self):
        outputs = [
            make_judge_output(passed=True, critical_issues=["missing_doctype"]),
            make_judge_output(passed=True),
            make_judge_output(passed=True),
        ]
        result = majority_vote(outputs)
        assert result.passed is False
        assert "missing_doctype" in result.critical_issues

    def test_averages_overall_score(self):
        outputs = [
            make_judge_output(score=8.0),
            make_judge_output(score=6.0),
            make_judge_output(score=7.0),
        ]
        result = majority_vote(outputs)
        assert result.overall_score == pytest.approx(7.0)

    def test_deduplicates_critical_issues(self):
        outputs = [
            make_judge_output(critical_issues=["missing_doctype"]),
            make_judge_output(critical_issues=["missing_doctype"]),
            make_judge_output(critical_issues=["missing_doctype"]),
        ]
        result = majority_vote(outputs)
        assert result.critical_issues.count("missing_doctype") == 1

    def test_unions_distinct_critical_issues(self):
        outputs = [
            make_judge_output(critical_issues=["issue_a"]),
            make_judge_output(critical_issues=["issue_b"]),
            make_judge_output(critical_issues=[]),
        ]
        result = majority_vote(outputs)
        assert "issue_a" in result.critical_issues
        assert "issue_b" in result.critical_issues

    def test_raises_on_fewer_than_two(self):
        with pytest.raises(ValueError, match="at least 2"):
            majority_vote([make_judge_output()])

    def test_averages_layer_scores(self):
        j1 = make_judge_output(score=10.0)
        j2 = make_judge_output(score=6.0)
        result = majority_vote([j1, j2])
        for ls in result.layer_scores:
            assert ls.score == pytest.approx(8.0)

    def test_uses_rationale_from_first_judge(self):
        j1 = make_judge_output()
        j1.rationale = "First judge rationale"
        j2 = make_judge_output()
        j2.rationale = "Second judge rationale"
        result = majority_vote([j1, j2])
        assert result.rationale == "First judge rationale"


# ── GEvalScorer ───────────────────────────────────────────────────────────────

class TestGEvalScorer:
    @pytest.mark.asyncio
    async def test_score_returns_judge_output(self):
        from packages.quality.layer4_judge.geval import GEvalScorer

        good_output = make_judge_output(passed=True, score=8.0)
        mock_litellm = _make_litellm_mock(return_value=_make_llm_response(good_output))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer()
            result = await scorer.score([{"title": "test artifact", "artifact_type": "lesson"}])

        assert isinstance(result, JudgeOutput)

    @pytest.mark.asyncio
    async def test_calls_litellm_num_judges_times(self):
        from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

        good_output = make_judge_output(passed=True, score=8.0)
        mock_litellm = _make_litellm_mock(return_value=_make_llm_response(good_output))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer(GEvalConfig(num_judges=3))
            await scorer.score([{"title": "test"}])

        assert mock_litellm.acompletion.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_when_all_judges_fail(self):
        from packages.quality.layer4_judge.geval import GEvalScorer

        mock_litellm = _make_litellm_mock(side_effect=RuntimeError("API error"))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer()
            with pytest.raises(ValueError, match="All judge calls failed"):
                await scorer.score([{"title": "test"}])

    @pytest.mark.asyncio
    async def test_continues_on_single_judge_failure(self):
        from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

        good_output = make_judge_output(passed=True, score=8.0)
        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            assert kwargs
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First judge failed")
            return _make_llm_response(good_output)

        mock_litellm = MagicMock()
        mock_litellm.acompletion = AsyncMock(side_effect=side_effect)
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer(GEvalConfig(num_judges=3))
            result = await scorer.score([{"title": "test"}])

        assert isinstance(result, JudgeOutput)

    @pytest.mark.asyncio
    async def test_uses_different_temperatures(self):
        from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

        good_output = make_judge_output(passed=True, score=8.0)
        mock_litellm = _make_litellm_mock(return_value=_make_llm_response(good_output))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer(GEvalConfig(num_judges=3))
            await scorer.score([{"title": "test"}])

        temps = [call.kwargs["temperature"] for call in mock_litellm.acompletion.call_args_list]
        assert len(set(temps)) > 1

    @pytest.mark.asyncio
    async def test_metadata_tags_include_reviewer(self):
        from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

        good_output = make_judge_output(passed=True, score=8.0)
        mock_litellm = _make_litellm_mock(return_value=_make_llm_response(good_output))
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            scorer = GEvalScorer(GEvalConfig(num_judges=1))
            await scorer.score([{"title": "test"}])

        tags = mock_litellm.acompletion.call_args.kwargs["extra_body"]["metadata"]["tags"]
        assert any("agent:reviewer" in t for t in tags)
        assert any("pipeline:oh-my-class" in t for t in tags)
