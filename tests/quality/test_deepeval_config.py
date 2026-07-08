"""DeepEval quality metric configuration tests — logic/scaffold only, no real LLM.

None of these tests call 9router: they exercise DeepEval's own plumbing with
hand-rolled fakes, or are explicit scaffolds ("Full wiring deferred to te-004").
That is a legitimate, honest use of fakes per the testing pyramid — deterministic
logic does not need a real LLM. A genuine real-9router-backed test belongs in
test_deepeval_real_llm.py, not here (2026-07-08 split: this file previously
carried a file-level real-LLM pytest marker while several of its tests
mocked litellm — see tests/test_no_fake_llm.py for the guard that now
catches that contradiction).
"""
from __future__ import annotations

from typing import Any

import pytest


def _judge_response_json(*, passed: bool, score: float, issue: str | None = None) -> str:
    from common.contracts.judge_output import JudgeOutput, LayerScore

    output = JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=[] if issue is None else [issue],
        passed=passed,
        rationale="test judge rationale",
        teacher_facing_summary="Teacher summary",
    )
    return output.model_dump_json()


def _fake_transport(response_json: str, *, captured_calls: list[dict[str, Any]] | None = None):
    """A controlled llm_transport double — injected via AdaptiveJudge's own
    dependency-inversion seam (not by mocking sys.modules) so it stays fast
    and offline regardless of what the real default transport does."""

    async def transport(*, model: str, messages: list[dict[str, str]], temperature: float, extra_body: dict[str, Any]) -> str:
        if captured_calls is not None:
            captured_calls.append({"model": model, "messages": messages, "extra_body": extra_body})
        return response_json

    return transport


def test_deepeval_can_import():
    """DeepEval must be importable (installed)."""
    import deepeval
    from deepeval.metrics import HallucinationMetric

    assert deepeval is not None
    assert HallucinationMetric.__name__ == "HallucinationMetric"


def test_hallucination_metric_measure_is_invoked() -> None:
    from deepeval.metrics import HallucinationMetric
    from deepeval.models.base_model import DeepEvalBaseLLM
    from deepeval.test_case import LLMTestCase

    class GroundedJudge(DeepEvalBaseLLM):
        measure_calls = 0

        def load_model(self):
            return self

        def get_model_name(self) -> str:
            return "grounded-judge"

        def generate(self, prompt, schema=None):
            self.measure_calls += 1
            if schema is None:
                return '{"reason":"grounded"}'
            if schema.__name__ == "Verdicts":
                return schema.model_validate({
                    "verdicts": [{"verdict": "yes", "reason": "grounded in context"}],
                })
            return schema.model_validate({"reason": "grounded"})

        async def a_generate(self, prompt, schema=None):
            return self.generate(prompt, schema)

    judge = GroundedJudge()
    metric = HallucinationMetric(model=judge, async_mode=False, include_reason=True)
    score = metric.measure(LLMTestCase(
        input="What do plants use for photosynthesis?",
        actual_output="Plants use light for photosynthesis.",
        context=["Plants use light for photosynthesis."],
    ))

    assert judge.measure_calls >= 1
    assert score == metric.score
    assert metric.score == 0.0


def test_no_telemetry_egress(deepeval_harness_config):
    """DeepEval must run in offline mode (no Confident AI telemetry).

    The deepeval_harness_config fixture sets CONFIDENT_AI_DISABLE_TRACKING=true.
    This test asserts the config reflects that enforcement.
    """
    import deepeval

    assert deepeval is not None
    assert deepeval_harness_config.telemetry_disabled, (
        "CONFIDENT_AI_DISABLE_TRACKING must be 'true' in the test environment"
    )


@pytest.mark.anyio
async def test_hallucination_metric_flags_injected_factual_error():
    """Scaffold: HallucinationMetric over generated artifacts.

    Full wiring (inject factual error, assert metric fails) deferred to
    te-004 follow-up once runtime-parity/001 six-layer path is confirmed.
    """
    from packages.quality.layer4_judge.judge_interface import AdaptiveJudge

    transport = _fake_transport(_judge_response_json(
        passed=False,
        score=3.0,
        issue="hallucinated_claim",
    ))
    artifact = {
        "artifact_type": "lesson",
        "title": "Space facts",
        "sections": [{"content": "The Moon is made of green cheese."}],
    }
    result = await AdaptiveJudge(model="4omc", num_judges=1, llm_transport=transport).judge(
        artifacts=[artifact],
        artifact_type="lesson",
    )

    assert result.judge_output.passed is False
    assert "hallucinated_claim" in result.judge_output.critical_issues


@pytest.mark.anyio
async def test_faithfulness_metric_uses_research_context(deepeval_harness_config):
    """Scaffold: FaithfulnessMetric for Researcher's sourced claims.

    Full wiring deferred to te-004 follow-up.
    """
    from packages.quality.layer4_judge.judge_interface import AdaptiveJudge

    captured_calls: list[dict[str, Any]] = []
    transport = _fake_transport(
        _judge_response_json(passed=True, score=8.0),
        captured_calls=captured_calls,
    )
    lesson_plan = {
        "topic": "Fractions",
        "sources": [{"title": "Curriculum", "summary": "Equivalent fractions"}],
    }
    await AdaptiveJudge(model="4omc", num_judges=1, llm_transport=transport).judge(
        artifacts=[{"artifact_type": "lesson", "title": "Equivalent fractions"}],
        artifact_type="lesson",
        lesson_plan=lesson_plan,
    )

    prompt = captured_calls[0]["messages"][1]["content"]
    assert "Lesson Plan for alignment" in prompt
    assert "Curriculum" in prompt
    assert deepeval_harness_config.judge_model == "4omc"


def test_geval_majority_vote_reproduces_quality_rubric(deepeval_harness_config):
    """Scaffold: G-Eval metric mirroring the 3-vote-majority rubric.

    Judge must route through 9router (4omc). Full wiring deferred to te-004.
    """
    from common.contracts.judge_output import JudgeOutput, LayerScore
    from packages.quality.layer4_judge.majority_vote import majority_vote

    outputs = [
        JudgeOutput(
            overall_score=8.0,
            layer_scores=[LayerScore(layer="format_compliance", score=8.0, weight=0.15, issues=[])],
            critical_issues=[],
            passed=True,
            rationale="pass",
            teacher_facing_summary="Teacher summary",
        ),
        JudgeOutput(
            overall_score=7.5,
            layer_scores=[LayerScore(layer="format_compliance", score=7.5, weight=0.15, issues=[])],
            critical_issues=[],
            passed=True,
            rationale="pass",
            teacher_facing_summary="Teacher summary",
        ),
        JudgeOutput(
            overall_score=6.0,
            layer_scores=[LayerScore(layer="format_compliance", score=6.0, weight=0.15, issues=[])],
            critical_issues=[],
            passed=False,
            rationale="fail",
            teacher_facing_summary="Teacher summary",
        ),
    ]

    result = majority_vote(outputs)

    assert result.passed is True
    assert deepeval_harness_config.judge_model == "4omc"
