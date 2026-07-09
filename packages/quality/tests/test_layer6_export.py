"""Tests for layer6_export — deterministic checks + 3-judge majority consensus.

All tests use deterministic fake-LLM transports — no real LLM calls.
"""

from __future__ import annotations

from typing import Any

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.quality.layer6_export.export_validator import (
    ExportValidator,
    check_export_readiness,
)


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
        rationale="Export readiness evaluation",
        teacher_facing_summary="Artifacts are export-ready.",
    )


def _make_failing_judge_output(score: float = 5.0) -> JudgeOutput:
    """Build a failing JudgeOutput with the given overall score (no critical issues)."""
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=[],
        passed=score >= 7.0,
        rationale="Artifacts below export threshold.",
        teacher_facing_summary="Artifacts need improvement before export.",
    )


def _make_fake_llm_transport(*outputs: JudgeOutput):
    """Build a fake LLM transport returning pre-built JudgeOutputs in sequence."""
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
        idx = call_count % len(outputs_list)
        call_count += 1
        return outputs_list[idx].model_dump_json()

    return fake_transport


def _valid_artifacts() -> list[dict[str, Any]]:
    """Artifacts that pass all deterministic format-requirement checks."""
    return [
        {"artifact_type": "lesson", "title": "Test Lesson"},
        {"artifact_type": "quiz", "title": "Test Quiz"},
    ]


def _missing_artifacts() -> list[dict[str, Any]]:
    """Artifacts missing required types for gift format (needs quiz)."""
    return [{"artifact_type": "lesson"}]


# ── Deterministic pre-check tests ─────────────────────────────────────────────


class TestDeterministicPreCheck:
    """Deterministic checks run first (fail-fast) before any judge calls."""

    def test_deterministic_pass_leads_to_judge_consensus(self) -> None:
        """When deterministic checks pass, validate() should proceed to judges."""
        result = check_export_readiness(_valid_artifacts(), ["html"])
        assert result.passed

    def test_deterministic_fail_returns_format_issues(self) -> None:
        result = check_export_readiness(_missing_artifacts(), ["gift"])
        assert not result.passed
        assert "gift" in result.format_issues

    def test_no_formats_requested_passes_deterministic(self) -> None:
        assert check_export_readiness([{"artifact_type": "lesson"}], []).passed


# ── 3-judge majority consensus tests ─────────────────────────────────────────


class TestJudgeConsensus:
    """3-judge majority pass: 2/3 must pass for export to proceed."""

    @pytest.mark.asyncio
    async def test_validate_calls_three_judges(self) -> None:
        """validate() must invoke the LLM judge exactly 3 times."""
        call_count = 0

        async def counting_transport(
            *,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            extra_body: dict[str, Any],
        ) -> str:
            nonlocal call_count
            call_count += 1
            return _make_passing_judge_output(8.0).model_dump_json()

        validator = ExportValidator(llm_transport=counting_transport)
        await validator.validate(_valid_artifacts(), ["html"])

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_two_of_three_pass_is_overall_pass(self) -> None:
        """2 passing + 1 failing → consensus passes (2/3 ≥ 0.67)."""
        j_pass1 = _make_passing_judge_output(8.0)
        j_pass2 = _make_passing_judge_output(8.5)
        j_fail = _make_failing_judge_output(5.0)

        fake_llm = _make_fake_llm_transport(j_pass1, j_pass2, j_fail)
        validator = ExportValidator(llm_transport=fake_llm)

        result = await validator.validate(_valid_artifacts(), ["html"])

        assert result.passed is True
        assert len(result.judge_results) == 1  # Aggregated consensus result

    @pytest.mark.asyncio
    async def test_one_of_three_pass_is_overall_fail(self) -> None:
        """1 passing + 2 failing → consensus fails."""
        j_pass = _make_passing_judge_output(8.0)
        j_fail1 = _make_failing_judge_output(5.0)
        j_fail2 = _make_failing_judge_output(4.0)

        fake_llm = _make_fake_llm_transport(j_pass, j_fail1, j_fail2)
        validator = ExportValidator(llm_transport=fake_llm)

        result = await validator.validate(_valid_artifacts(), ["html"])

        assert result.passed is False
        assert len(result.judge_results) == 1  # Aggregated consensus result

    @pytest.mark.asyncio
    async def test_three_of_three_pass_is_overall_pass(self) -> None:
        """All 3 passing → consensus passes."""
        fake_llm = _make_fake_llm_transport(
            _make_passing_judge_output(8.0),
            _make_passing_judge_output(9.0),
            _make_passing_judge_output(7.5),
        )
        validator = ExportValidator(llm_transport=fake_llm)

        result = await validator.validate(_valid_artifacts(), ["html"])

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_zero_of_three_pass_is_overall_fail(self) -> None:
        """All 3 failing → consensus fails."""
        fake_llm = _make_fake_llm_transport(
            _make_failing_judge_output(5.0),
            _make_failing_judge_output(4.0),
            _make_failing_judge_output(6.0),
        )
        validator = ExportValidator(llm_transport=fake_llm)

        result = await validator.validate(_valid_artifacts(), ["html"])

        assert result.passed is False

    @pytest.mark.asyncio
    async def test_deterministic_failure_skips_judges(self) -> None:
        """When deterministic checks fail, no LLM judge calls are made."""
        call_count = 0

        async def counting_transport(
            *,
            model: str,
            messages: list[dict[str, str]],
            temperature: float,
            extra_body: dict[str, Any],
        ) -> str:
            nonlocal call_count
            call_count += 1
            return _make_passing_judge_output(8.0).model_dump_json()

        validator = ExportValidator(llm_transport=counting_transport)
        result = await validator.validate(_missing_artifacts(), ["gift"])

        assert result.passed is False
        assert call_count == 0  # Judges must NOT be called

    @pytest.mark.asyncio
    async def test_consensus_threshold_from_gate_config(self) -> None:
        """export_consensus_threshold from GateConfig is wired into majority vote."""
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.export_consensus_threshold == 0.67
        assert config.export_min_score == 7.0

        validator = ExportValidator(
            llm_transport=_make_fake_llm_transport(
                _make_passing_judge_output(8.0),
                _make_passing_judge_output(8.5),
                _make_failing_judge_output(5.0),
            ),
            required_pass_rate=config.export_consensus_threshold,
        )
        result = await validator.validate(_valid_artifacts(), ["html"])

        # 2/3 = 0.667 ≥ 0.67 threshold → passes
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_judge_results_populated_on_consensus(self) -> None:
        """judge_results contains per-judge output dicts."""
        fake_llm = _make_fake_llm_transport(
            _make_passing_judge_output(8.0),
            _make_passing_judge_output(9.0),
            _make_passing_judge_output(7.5),
        )
        validator = ExportValidator(llm_transport=fake_llm)

        result = await validator.validate(_valid_artifacts(), ["html"])

        assert len(result.judge_results) == 1  # Aggregated consensus result
        for jr in result.judge_results:
            assert "overall_score" in jr
            assert "passed" in jr
