"""Tests for adaptive judge interface (task 6) — rubric selection, provenance,
hard-block override prevention, and judge-unavailable path.

All tests use deterministic fake-LLM transports — no real LLM calls.
"""

from __future__ import annotations

from typing import Any

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from common.contracts.rubric import Rubric
from packages.quality.layer4_judge.hard_blocks import enforce_hard_blocks
from packages.quality.layer4_judge.judge_interface import (
    HARD_BLOCK_CODES,
    AdaptiveJudge,
    JudgeResult,
    JudgeUnavailableError,
    UnavailableStrategy,
)
from packages.quality.layer4_judge.judge_policy import JudgePolicyContext, judge_policy_decision
from packages.quality.layer4_judge.rubric_selector import RubricSelector

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_passing_judge_output(score: float = 8.0) -> JudgeOutput:
    """Build a passing JudgeOutput with the given overall score."""
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=[],
        passed=score >= 7.0,
        rationale="Test rationale",
        teacher_facing_summary="Teacher summary",
    )


def _make_fake_llm_transport(*outputs: JudgeOutput):
    """Build a fake LLM transport that returns pre-built JudgeOutputs in sequence.

    Each call returns the next output in the list, cycling if more calls
    than outputs are made.
    """
    call_count = 0
    outputs_list = list(outputs)

    async def fake_transport(
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        extra_body: dict[str, Any],
    ) -> str:
        nonlocal call_count
        assert model
        assert messages
        assert temperature >= 0.0
        assert extra_body
        idx = call_count % len(outputs_list)
        call_count += 1
        return outputs_list[idx].model_dump_json()

    return fake_transport


async def _failing_transport(**kwargs: Any) -> str:
    """Fake LLM transport that always raises."""
    assert kwargs
    raise ConnectionError("LLM service unreachable")


# ── RubricSelector tests ─────────────────────────────────────────────────────

class TestRubricSelector:
    def test_select_returns_rubric_for_known_type(self):
        selector = RubricSelector()
        rubric = selector.select("quiz")
        assert isinstance(rubric, Rubric)
        assert rubric.version_id == "rubric-quiz"
        assert len(rubric.criteria) == 3

    def test_select_default_for_unknown_type(self):
        selector = RubricSelector()
        rubric = selector.select("unknown_type_xyz")
        assert rubric.version_id == "rubric-unknown_type_xyz"
        # Should still have 3 criteria (base criteria)
        assert len(rubric.criteria) == 3

    def test_select_with_failure_context_changes_version_id(self):
        selector = RubricSelector()
        rubric = selector.select("quiz", ["answer_key_leakage"])
        assert rubric.version_id == "rubric-quiz-answer_key_leakage"

    def test_select_composes_contextual_version_id(self):
        selector = RubricSelector()
        rubric = selector.select(
            "quiz",
            ["answer_key_leakage"],
            subject="Math",
            locale="vi-VN",
            curriculum="CT 2018",
            risk_level="rigorous",
        )

        assert rubric.version_id == (
            "rubric-quiz-subject-math-locale-vi-vn-curriculum-ct-2018-"
            "risk-rigorous-answer_key_leakage"
        )

    def test_select_with_multiple_failures_sorts_alphabetically(self):
        selector = RubricSelector()
        rubric = selector.select("lesson", ["pii_leakage", "missing_doctype"])
        # Should be sorted: missing_doctype, pii_leakage
        assert rubric.version_id == "rubric-lesson-missing_doctype-pii_leakage"

    def test_failure_context_boosts_content_quality_weight(self):
        selector = RubricSelector()
        rubric_default = selector.select("lesson")
        rubric_boosted = selector.select("lesson", ["answer_key_leakage"])

        # Find content_quality criterion in both
        cq_default = next(c for c in rubric_default.criteria if c.name == "content_quality")
        cq_boosted = next(c for c in rubric_boosted.criteria if c.name == "content_quality")

        assert cq_boosted.weight > cq_default.weight

    def test_failure_context_boosts_presentation_weight(self):
        selector = RubricSelector()
        rubric_default = selector.select("lesson")
        rubric_boosted = selector.select("lesson", ["missing_doctype"])

        pres_default = next(c for c in rubric_default.criteria if c.name == "presentation")
        pres_boosted = next(c for c in rubric_boosted.criteria if c.name == "presentation")

        assert pres_boosted.weight > pres_default.weight

    def test_rubric_weights_sum_to_one(self):
        selector = RubricSelector()
        for artifact_type in ["lesson", "quiz", "worksheet", "drill", "recap", "infographic"]:
            rubric = selector.select(artifact_type)
            total = sum(c.weight for c in rubric.criteria)
            assert abs(total - 1.0) < 0.01, (
                f"Rubric for {artifact_type} weights sum to {total}"
            )

    def test_weights_sum_to_one_with_failure_context(self):
        selector = RubricSelector()
        rubric = selector.select("quiz", ["answer_key_leakage", "missing_doctype"])
        total = sum(c.weight for c in rubric.criteria)
        assert abs(total - 1.0) < 0.01

    def test_registry_caches_built_rubrics(self):
        selector = RubricSelector()
        r1 = selector.select("quiz")
        r2 = selector.select("quiz")
        assert r1 is r2  # Same object from registry cache

    def test_registry_increments_with_new_rubrics(self):
        selector = RubricSelector()
        initial_count = len(selector.registry)
        selector.select("quiz", ["answer_key_leakage"])
        assert len(selector.registry) > initial_count


# ── Hard block enforcement tests ──────────────────────────────────────────────

class TestHardBlockEnforcement:
    def test_no_hard_blocks_passes_through(self):
        output = _make_passing_judge_output(8.0)
        result, blocked, violations = enforce_hard_blocks(output, [], teacher_approved=True)
        assert blocked is False
        assert violations == []
        assert result.passed is True

    def test_missing_doctype_forces_fail(self):
        output = _make_passing_judge_output(9.5)  # Near-perfect LLM score
        result, blocked, violations = enforce_hard_blocks(
            output, ["missing_doctype"], teacher_approved=True
        )
        assert blocked is True
        assert result.passed is False
        assert "missing_doctype" in violations
        assert "missing_doctype" in result.critical_issues

    def test_external_assets_forces_fail(self):
        output = _make_passing_judge_output(9.0)
        result, blocked, violations = enforce_hard_blocks(
            output, ["external_assets"], teacher_approved=True
        )
        assert blocked is True
        assert result.passed is False
        assert "external_assets" in violations

    def test_answer_key_leakage_forces_fail(self):
        output = _make_passing_judge_output(9.0)
        result, blocked, _violations = enforce_hard_blocks(
            output, ["answer_key_leakage"], teacher_approved=True
        )
        assert blocked is True
        assert result.passed is False

    def test_pii_leakage_forces_fail(self):
        output = _make_passing_judge_output(9.0)
        result, blocked, _violations = enforce_hard_blocks(
            output, ["pii_leakage"], teacher_approved=True
        )
        assert blocked is True
        assert result.passed is False

    def test_high_llm_score_cannot_override_hard_block(self):
        """THE CRITICAL TEST: Even a perfect 10.0 LLM score cannot override hard blocks."""
        perfect_output = JudgeOutput(
            overall_score=10.0,
            layer_scores=[
                LayerScore(layer="format_compliance", score=10.0, weight=0.15),
                LayerScore(layer="content_quality", score=10.0, weight=0.55),
                LayerScore(layer="presentation", score=10.0, weight=0.30),
            ],
            critical_issues=[],
            passed=True,
            rationale="Perfect score",
            teacher_facing_summary="Teacher summary",
        )
        result, blocked, violations = enforce_hard_blocks(
            perfect_output, ["missing_doctype", "external_assets"], teacher_approved=True
        )
        assert result.passed is False
        assert blocked is True
        assert len(violations) == 2

    def test_teacher_not_approved_forces_fail(self):
        output = _make_passing_judge_output(9.0)
        result, blocked, violations = enforce_hard_blocks(
            output, [], teacher_approved=False
        )
        assert blocked is True
        assert result.passed is False
        assert "teacher_gate_not_approved" in violations

    def test_teacher_not_approved_plus_hard_blocks(self):
        output = _make_passing_judge_output(9.0)
        result, blocked, violations = enforce_hard_blocks(
            output, ["missing_doctype"], teacher_approved=False
        )
        assert blocked is True
        assert result.passed is False
        assert len(violations) == 2  # both missing_doctype and teacher_gate

    def test_non_hard_block_issues_not_forced_fail(self):
        """Issues that are NOT in the hard block set do not force failure."""
        output = _make_passing_judge_output(8.0)
        result, blocked, _violations = enforce_hard_blocks(
            output, ["accessibility_warning", "minor_typo"], teacher_approved=True
        )
        assert blocked is False
        assert result.passed is True

    def test_existing_critical_issues_preserved(self):
        output = _make_passing_judge_output(8.0)
        output.critical_issues = ["pre_existing_issue"]
        result, _, _ = enforce_hard_blocks(
            output, ["missing_doctype"], teacher_approved=True
        )
        assert "pre_existing_issue" in result.critical_issues
        assert "missing_doctype" in result.critical_issues

    def test_rationale_appended_with_override_info(self):
        output = _make_passing_judge_output(8.0)
        result, _, _ = enforce_hard_blocks(
            output, ["missing_doctype"], teacher_approved=True
        )
        assert "[Deterministic override:" in result.rationale


# ── AdaptiveJudge integration tests ──────────────────────────────────────────

class TestAdaptiveJudge:
    def test_policy_decision_triggers_for_risk_deterministic_and_borderline(self):
        decision = judge_policy_decision(JudgePolicyContext(
            artifact_type="quiz",
            deterministic_issues=("answer_key_leakage",),
            risk_level="high",
            borderline_score=7.0,
        ))

        assert decision.should_judge is True
        assert decision.reasons == ("risk:high", "deterministic_issues", "borderline_score")

    @pytest.mark.asyncio
    async def test_judge_returns_judge_result_with_provenance(self):
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(8.0))
        judge = AdaptiveJudge(
            llm_transport=fake_llm,
            num_judges=1,
            pass_threshold=7.0,
        )
        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz", "title": "Test Quiz"}],
            artifact_type="quiz",
        )

        assert isinstance(result, JudgeResult)
        assert isinstance(result.judge_output, JudgeOutput)
        assert result.rubric_version == "rubric-quiz"
        assert result.llm_available is True
        assert result.deterministic_blocked is False

    @pytest.mark.asyncio
    async def test_judge_selects_rubric_by_artifact_type(self):
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(8.0))
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=1)

        result_quiz = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
        )
        assert result_quiz.rubric_version == "rubric-quiz"

        result_worksheet = await judge.judge(
            artifacts=[{"artifact_type": "worksheet"}],
            artifact_type="worksheet",
        )
        assert result_worksheet.rubric_version == "rubric-worksheet"

    @pytest.mark.asyncio
    async def test_judge_selects_rubric_with_failure_context(self):
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(8.0))
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=1)

        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
            deterministic_issues=["answer_key_leakage"],
        )
        assert result.rubric_version == "rubric-quiz-answer_key_leakage"

    @pytest.mark.asyncio
    async def test_judge_enforces_hard_blocks_overrides_llm_score(self):
        """LLM returns score 9.0 (pass) but hard block forces fail."""
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(9.0))
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=1)

        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
            deterministic_issues=["missing_doctype"],
        )

        assert result.judge_output.passed is False
        assert result.deterministic_blocked is True
        assert "missing_doctype" in result.hard_block_violations
        # LLM score is preserved for diagnostics
        assert result.judge_output.overall_score == 9.0

    @pytest.mark.asyncio
    async def test_judge_enforces_teacher_gate_state(self):
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(9.0))
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=1)

        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
            teacher_approved=False,
        )

        assert result.judge_output.passed is False
        assert result.deterministic_blocked is True
        assert "teacher_gate_not_approved" in result.hard_block_violations

    @pytest.mark.asyncio
    async def test_judge_fail_closed_raises_on_llm_unavailable(self):
        judge = AdaptiveJudge(
            llm_transport=_failing_transport,
            num_judges=1,
            unavailable_strategy=UnavailableStrategy.FAIL_CLOSED,
        )

        with pytest.raises(JudgeUnavailableError, match="LLM judge unavailable"):
            await judge.judge(
                artifacts=[{"artifact_type": "quiz"}],
                artifact_type="quiz",
            )

    @pytest.mark.asyncio
    async def test_judge_deterministic_only_returns_fail_without_llm(self):
        judge = AdaptiveJudge(
            llm_transport=_failing_transport,
            num_judges=1,
            unavailable_strategy=UnavailableStrategy.USE_DETERMINISTIC_ONLY,
        )

        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
        )

        assert result.judge_output.passed is False
        assert result.llm_available is False
        assert result.judge_output.overall_score == 0.0
        assert "llm_judge_unavailable" in result.judge_output.critical_issues

    @pytest.mark.asyncio
    async def test_judge_majority_vote_across_multiple_calls(self):
        """3 judge calls returning different scores → majority vote aggregation."""
        j1 = _make_passing_judge_output(8.0)
        j2 = _make_passing_judge_output(8.0)
        j3 = _make_passing_judge_output(6.0)  # One lower score

        fake_llm = _make_fake_llm_transport(j1, j2, j3)
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=3)

        result = await judge.judge(
            artifacts=[{"artifact_type": "lesson"}],
            artifact_type="lesson",
        )

        # 2/3 passed → majority pass
        assert result.judge_output.passed is True
        assert result.llm_available is True

    @pytest.mark.asyncio
    async def test_judge_preserves_rubric_provenance_through_full_pipeline(self):
        """Provenance chain: artifact_type + failure_context → rubric version → result."""
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(8.0))
        selector = RubricSelector()
        judge = AdaptiveJudge(
            llm_transport=fake_llm,
            rubric_selector=selector,
            num_judges=1,
        )

        result = await judge.judge(
            artifacts=[{"artifact_type": "drill"}],
            artifact_type="drill",
            deterministic_issues=["pii_leakage"],
        )

        assert result.rubric_version == "rubric-drill-pii_leakage"
        assert "drill" in result.rubric_description.lower()
        assert result.rubric_description != ""

    @pytest.mark.asyncio
    async def test_judge_exposes_policy_and_contextual_rubric_provenance(self):
        fake_llm = _make_fake_llm_transport(_make_passing_judge_output(8.0))
        judge = AdaptiveJudge(llm_transport=fake_llm, num_judges=1)

        result = await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
            deterministic_issues=["answer_key_leakage"],
            subject="Math",
            locale="vi-VN",
            curriculum="CT 2018",
            risk_level="rigorous",
            borderline_score=7.0,
        )

        assert result.rubric_version == (
            "rubric-quiz-subject-math-locale-vi-vn-curriculum-ct-2018-"
            "risk-rigorous-answer_key_leakage"
        )
        assert result.policy_triggered is True
        assert result.policy_reasons == (
            "risk:rigorous",
            "deterministic_issues",
            "borderline_score",
        )


# ── Hard block code coverage tests ───────────────────────────────────────────

class TestHardBlockCodeCoverage:
    """Verify all known hard block codes are in the enforcement set."""

    def test_all_quality_failure_classes_covered(self):
        from common.contracts.quality import QualityFailureClass

        # Every QualityFailureClass that should be a hard block
        expected_hard_blocks = {
            QualityFailureClass.SCHEMA_INVALID.value,
            QualityFailureClass.ANSWER_KEY_LEAKAGE.value,
            QualityFailureClass.PII_LEAKAGE.value,
            QualityFailureClass.EXTERNAL_ASSET.value,
            QualityFailureClass.MISSING_DOCTYPE.value,
        }
        # These must be in HARD_BLOCK_CODES
        assert expected_hard_blocks.issubset(HARD_BLOCK_CODES)

    def test_compliance_policy_hard_blocks_covered(self):
        from packages.quality.compliance_policy import COMPLIANCE_HARD_BLOCK_CODES

        # At minimum, these must overlap
        overlap = COMPLIANCE_HARD_BLOCK_CODES & HARD_BLOCK_CODES
        assert "missing_doctype" in overlap
        assert "external_assets" in overlap
        assert "answer_key_leakage" in overlap


# ── LLM transport metadata tests ─────────────────────────────────────────────

class TestLLMTransportMetadata:
    @pytest.mark.asyncio
    async def test_llm_calls_include_rubric_version_tag(self):
        """Verify the LLM transport receives the rubric version in metadata."""
        received_tags: list[list[str]] = []

        async def capturing_transport(
            *,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            extra_body: dict[str, Any],
        ) -> str:
            assert model
            assert messages
            assert temperature >= 0.0
            received_tags.append(extra_body["metadata"]["tags"])
            return _make_passing_judge_output(8.0).model_dump_json()

        judge = AdaptiveJudge(llm_transport=capturing_transport, num_judges=1)
        await judge.judge(
            artifacts=[{"artifact_type": "quiz"}],
            artifact_type="quiz",
        )

        assert len(received_tags) == 1
        tags = received_tags[0]
        assert any("rubric:rubric-quiz" in t for t in tags)
        assert any("agent:reviewer" in t for t in tags)

    @pytest.mark.asyncio
    async def test_llm_calls_include_different_temperatures(self):
        """Verify each judge call uses a different temperature for diversity."""
        temps: list[float] = []

        async def capturing_transport(
            *,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            extra_body: dict[str, Any],
        ) -> str:
            assert model
            assert messages
            assert extra_body
            temps.append(temperature)
            return _make_passing_judge_output(8.0).model_dump_json()

        judge = AdaptiveJudge(llm_transport=capturing_transport, num_judges=3)
        await judge.judge(
            artifacts=[{"artifact_type": "lesson"}],
            artifact_type="lesson",
        )

        assert len(temps) == 3
        assert len(set(temps)) == 3  # All different
