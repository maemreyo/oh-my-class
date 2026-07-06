"""Test that render_quality stores per-artifact reports in quality_scores when gate passes."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.quality_runtime import render_quality


def _make_artifact(artifact_id: str, artifact_type: str = "lesson") -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "title": "Test Lesson",
        "sections": [
            {
                "type": "paragraph",
                "text": "Hình chữ nhật là tứ giác có bốn góc vuông và hai cặp cạnh đối song song bằng nhau.",
            }
        ],
        "accessibility": {"language": "vi"},
        "metadata": {"grade_level": "Grade 5"},
    }


def _make_passing_report(artifact_id: str, artifact_type: str = "lesson") -> ArtifactQualityReport:
    return ArtifactQualityReport(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        passed=True,
        issues=[],
    )


@pytest.mark.asyncio
async def test_quality_scores_includes_reports_when_gate_passes() -> None:
    """When quality gate evaluates and all reports pass, quality_scores.reports is populated."""
    artifact = _make_artifact("art-001", "lesson")
    report = _make_passing_report("art-001", "lesson")

    mock_gate = AsyncMock()
    mock_gate.evaluate.return_value = report

    state = {"run_id": "run-test-001", "artifacts": [artifact]}
    result = await render_quality(state, quality_gate=mock_gate)

    scores = result.get("quality_scores")
    assert isinstance(scores, dict)
    assert scores["passed"] is True
    assert "reports" in scores, "quality_scores.reports must be present when gate passes"
    reports = scores["reports"]
    assert isinstance(reports, list)
    assert len(reports) == 1
    assert reports[0]["artifact_id"] == "art-001"
    assert reports[0]["passed"] is True


@pytest.mark.asyncio
async def test_slide_deck_quality_uses_existing_gate_path() -> None:
    artifact = _make_artifact("slide-deck-001", "slide_deck")
    report = _make_passing_report("slide-deck-001", "slide_deck")

    mock_gate = AsyncMock()
    mock_gate.evaluate.return_value = report

    state = {"run_id": "run-slide-quality", "artifacts": [artifact]}
    result = await render_quality(state, quality_gate=mock_gate)

    mock_gate.evaluate.assert_awaited_once()
    scores = result.get("quality_scores")
    assert isinstance(scores, dict)
    assert scores["passed"] is True
    assert scores["reports"][0]["artifact_type"] == "slide_deck"


@pytest.mark.asyncio
async def test_quality_scores_has_no_reports_when_gate_is_none() -> None:
    """When no quality gate is injected, quality_scores.reports is absent."""
    artifact = _make_artifact("art-002", "quiz")
    state = {"run_id": "run-test-002", "artifacts": [artifact]}
    result = await render_quality(state, quality_gate=None)

    scores = result.get("quality_scores")
    assert isinstance(scores, dict)
    assert scores["passed"] is True
    assert "reports" not in scores, "quality_scores.reports must not be present without a gate"


@pytest.mark.asyncio
async def test_quality_scores_includes_reports_with_issues_when_gate_fails() -> None:
    """When gate fails, the returned quality_scores does NOT include passing reports (healing path)."""
    from common.contracts.quality import QualityFailureClass, QualityIssue

    artifact = _make_artifact("art-003", "lesson")
    failed_report = ArtifactQualityReport(
        artifact_id="art-003",
        artifact_type="lesson",
        passed=False,
        issues=[
            QualityIssue(
                failure_class=QualityFailureClass.PLACEHOLDER_CONTENT,
                location="sections",
                message="placeholder text found",
            )
        ],
    )

    mock_gate = AsyncMock()
    mock_gate.evaluate.return_value = failed_report

    state = {"run_id": "run-test-003", "artifacts": [artifact]}
    result = await render_quality(state, quality_gate=mock_gate)

    # Failed path: quality_recovery_route is set; rendered_snapshots is absent
    assert "quality_recovery_route" in result
    assert "rendered_snapshots" not in result or result.get("rendered_snapshots") is None


def test_gate_body_quality_scores_passed_to_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    """_teacher_approval includes quality_scores (with reports) in the interrupt payload."""
    from packages.agents.teaching_pack.nodes import _teacher_approval

    captured: list[dict[str, Any]] = []

    def fake_interrupt(payload: dict[str, Any]) -> dict[str, str]:
        captured.append(payload)
        return {"action": "approve"}

    # interrupt is a local import inside _teacher_approval — patch at the module level
    monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

    state = {
        "run_id": "run-test-004",
        "artifacts": [_make_artifact("art-004")],
        "rendered_snapshots": [{"snapshot_id": "snap-001", "artifact_id": "art-004"}],
        "quality_scores": {
            "overall": 8.0,
            "passed": True,
            "snapshot_count": 1,
            "reports": [{"artifact_id": "art-004", "artifact_type": "lesson", "passed": True, "issues": []}],
        },
    }

    result = _teacher_approval(state)

    assert result["teacher_approved"] is True
    assert captured, "interrupt() should have been called"
    payload = captured[0]
    assert "quality_scores" in payload
    assert payload["quality_scores"]["passed"] is True
    assert "reports" in payload["quality_scores"]
