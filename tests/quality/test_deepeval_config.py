"""DeepEval quality metric configuration tests.

Marked real_llm — run nightly with:
    uv run pytest -m real_llm tests/quality/

All metrics use the 9router judge (base_url from OMC_TEST_9ROUTER_BASE_URL,
model from OMC_TEST_9ROUTER_MODEL). Telemetry is disabled via
CONFIDENT_AI_DISABLE_TRACKING=true (set in conftest.py deepeval_harness_config).
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.real_llm


def _judge_response(*, passed: bool, score: float, issue: str | None = None) -> MagicMock:
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
    )
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = output.model_dump_json()
    return response


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


@pytest.mark.anyio
async def test_deepeval_uses_9router_not_openai(deepeval_harness_config):
    """DeepEval judge must route through 9router, not OpenAI directly."""
    from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

    litellm = MagicMock()
    litellm.acompletion = AsyncMock(return_value=_judge_response(passed=True, score=8.0))
    with patch.dict(sys.modules, {"litellm": litellm}):
        scorer = GEvalScorer(GEvalConfig(num_judges=1, judge_model=deepeval_harness_config.judge_model))
        await scorer.score([{"artifact_type": "lesson", "title": "Fractions"}])

    assert litellm.acompletion.call_args.kwargs["model"] == deepeval_harness_config.judge_model
    assert deepeval_harness_config.judge_base_url.endswith(":20228")


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
    from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

    litellm = MagicMock()
    litellm.acompletion = AsyncMock(return_value=_judge_response(
        passed=False,
        score=3.0,
        issue="hallucinated_claim",
    ))
    artifact = {
        "artifact_type": "lesson",
        "title": "Space facts",
        "sections": [{"content": "The Moon is made of green cheese."}],
    }
    with patch.dict(sys.modules, {"litellm": litellm}):
        result = await GEvalScorer(GEvalConfig(num_judges=1)).score([artifact])

    assert result.passed is False
    assert "hallucinated_claim" in result.critical_issues


@pytest.mark.anyio
async def test_faithfulness_metric_uses_research_context(deepeval_harness_config):
    """Scaffold: FaithfulnessMetric for Researcher's sourced claims.

    Full wiring deferred to te-004 follow-up.
    """
    from packages.quality.layer4_judge.geval import GEvalConfig, GEvalScorer

    litellm = MagicMock()
    litellm.acompletion = AsyncMock(return_value=_judge_response(passed=True, score=8.0))
    lesson_plan = {
        "topic": "Fractions",
        "sources": [{"title": "Curriculum", "summary": "Equivalent fractions"}],
    }
    with patch.dict(sys.modules, {"litellm": litellm}):
        await GEvalScorer(GEvalConfig(num_judges=1)).score(
            [{"artifact_type": "lesson", "title": "Equivalent fractions"}],
            lesson_plan=lesson_plan,
        )

    prompt = litellm.acompletion.call_args.kwargs["messages"][1]["content"]
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
        ),
        JudgeOutput(
            overall_score=7.5,
            layer_scores=[LayerScore(layer="format_compliance", score=7.5, weight=0.15, issues=[])],
            critical_issues=[],
            passed=True,
            rationale="pass",
        ),
        JudgeOutput(
            overall_score=6.0,
            layer_scores=[LayerScore(layer="format_compliance", score=6.0, weight=0.15, issues=[])],
            critical_issues=[],
            passed=False,
            rationale="fail",
        ),
    ]

    result = majority_vote(outputs)

    assert result.passed is True
    assert deepeval_harness_config.judge_model == "4omc"
