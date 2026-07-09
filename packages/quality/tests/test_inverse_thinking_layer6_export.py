from __future__ import annotations

from typing import Any

import pytest

from packages.quality.layer6_export.export_validator import ExportValidator


async def _passing_transport(*, model: str, messages: list[dict[str, str]], temperature: float, extra_body: dict[str, Any]) -> str:
    from common.contracts.judge_output import JudgeOutput, LayerScore
    output = JudgeOutput(
        overall_score=8.0,
        layer_scores=[
            LayerScore(layer="format_compliance", score=8.0, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=8.0, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=8.0, weight=0.30, issues=[]),
        ],
        critical_issues=[],
        passed=True,
        rationale="Test",
        teacher_facing_summary="Test",
    )
    return output.model_dump_json()


@pytest.mark.asyncio
async def test_inverse_thinking_h5p_readiness_fails_closed_when_semantics_are_lossy() -> None:
    validator = ExportValidator()

    result = await validator.validate(
        artifacts=[
            {"artifact_type": "lesson", "metadata": {"methodology": "inverse_thinking"}},
            {"artifact_type": "quiz", "metadata": {"methodology": "inverse_thinking"}},
            {"artifact_type": "drill", "metadata": {"methodology": "inverse_thinking"}},
        ],
        export_formats=["html", "gift", "h5p"],
    )

    assert not result.passed
    assert "h5p" in result.format_issues
    assert "cannot be preserved" in result.format_issues["h5p"][0]


@pytest.mark.asyncio
async def test_inverse_thinking_supported_formats_pass_readiness() -> None:
    validator = ExportValidator(llm_transport=_passing_transport)

    result = await validator.validate(
        artifacts=[
            {"artifact_type": "lesson", "metadata": {"methodology": "inverse_thinking"}},
            {"artifact_type": "quiz", "metadata": {"methodology": "inverse_thinking"}},
        ],
        export_formats=["html", "gift", "qti"],
    )

    assert result.passed
    assert result.format_issues == {}


@pytest.mark.asyncio
async def test_inverse_thinking_google_forms_readiness_reports_lossy_mapping() -> None:
    validator = ExportValidator()

    result = await validator.validate(
        artifacts=[{"artifact_type": "lesson", "methodology": "inverse_thinking"}],
        export_formats=["google_forms"],
    )

    assert not result.passed
    assert "lossy" in result.format_issues["google_forms"][0]
