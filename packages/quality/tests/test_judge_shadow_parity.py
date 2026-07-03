from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer
from packages.quality.layer4_judge.judge_interface import AdaptiveJudge


def _judge_output(score: float, *, passed: bool) -> JudgeOutput:
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15),
            LayerScore(layer="content_quality", score=score, weight=0.55),
            LayerScore(layer="presentation", score=score, weight=0.30),
        ],
        critical_issues=[] if passed else ["content_quality_regression"],
        passed=passed,
        rationale="Shadow judge rationale",
        teacher_facing_summary="Teacher-facing shadow summary.",
    )


def _litellm_response(output: JudgeOutput) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = output.model_dump_json()
    return response


@pytest.mark.asyncio
async def test_adaptive_judge_matches_geval_decision_on_shadow_runs() -> None:
    artifacts = [
        {"artifact_type": "lesson", "title": "Equivalent fractions", "sections": [{"content": "Students explain equivalent fractions."}]},
        {"artifact_type": "quiz", "title": "Fractions quiz", "sections": [{"content": "Three fraction questions."}]},
    ]
    lesson_plan = {"topic": "Equivalent fractions"}
    outputs = [_judge_output(8.0, passed=True), _judge_output(8.2, passed=True), _judge_output(6.5, passed=False)]

    legacy_litellm = MagicMock()
    legacy_litellm.acompletion = AsyncMock(side_effect=[_litellm_response(output) for output in outputs])
    with patch.dict(sys.modules, {"litellm": legacy_litellm}):
        legacy = await GEvalScorer(GEvalConfig(num_judges=3, judge_model="4omc")).score(
            artifacts,
            lesson_plan=lesson_plan,
        )

    adaptive_call_count = 0

    async def adaptive_transport(**kwargs: object) -> str:
        nonlocal adaptive_call_count
        assert kwargs
        index = adaptive_call_count
        adaptive_call_count += 1
        return outputs[index].model_dump_json()

    adaptive = await AdaptiveJudge(
        llm_transport=adaptive_transport,
        model="4omc",
        num_judges=3,
    ).judge(
        artifacts=artifacts,
        artifact_type="lesson",
        lesson_plan=lesson_plan,
    )

    assert adaptive.judge_output.passed is legacy.passed
    assert adaptive.judge_output.overall_score == pytest.approx(legacy.overall_score)
    assert adaptive.judge_output.critical_issues == legacy.critical_issues
    assert adaptive.judge_output.teacher_facing_summary == legacy.teacher_facing_summary
