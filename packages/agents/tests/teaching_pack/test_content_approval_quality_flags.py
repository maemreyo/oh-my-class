"""Test that render_quality stores per-artifact reports in quality_scores when gate passes."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.compliance import evaluate_compliance
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
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


async def _persist_artifacts(
    run_id: str, artifacts: list[dict[str, Any]],
) -> tuple[InMemoryArtifactContentStore, list[dict[str, Any]]]:
    """Persist raw artifact dicts into an in-memory store and return references."""
    store = InMemoryArtifactContentStore()
    references = []
    generation_id = f"{run_id}:artifact:1"
    for index, artifact in enumerate(artifacts, start=1):
        artifact_id = str(artifact.get("artifact_id", f"artifact-{index}"))
        parsed = ArtifactContent.model_validate(
            {k: v for k, v in artifact.items() if k != "artifact_id"},
        )
        ref = await store.persist(run_id, generation_id, parsed, artifact_id)
        references.append(ref.as_state())
    return store, references


@pytest.mark.asyncio
async def test_quality_scores_includes_reports_when_gate_passes() -> None:
    """When quality gate evaluates and all reports pass, quality_scores.reports is populated."""
    artifact = _make_artifact("art-001", "lesson")
    report = _make_passing_report("art-001", "lesson")

    mock_gate = AsyncMock()
    mock_gate.evaluate.return_value = report

    store, references = await _persist_artifacts("run-test-001", [artifact])
    state = {"run_id": "run-test-001", "artifact_references": references}
    result = await render_quality(state, quality_gate=mock_gate, content_store=store)

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

    store, references = await _persist_artifacts("run-slide-quality", [artifact])
    state = {"run_id": "run-slide-quality", "artifact_references": references}
    result = await render_quality(state, quality_gate=mock_gate, content_store=store)

    mock_gate.evaluate.assert_awaited_once()
    scores = result.get("quality_scores")
    assert isinstance(scores, dict)
    assert scores["passed"] is True
    assert scores["reports"][0]["artifact_type"] == "slide_deck"


@pytest.mark.asyncio
async def test_quality_scores_has_no_reports_when_gate_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no quality gate is injected, quality_scores.reports is absent."""
    from common.contracts.judge_output import JudgeOutput
    from packages.agents import llm

    async def fake_complete_json_chat(
        *,
        model: str,
        messages: list[object],
        temperature: float,
        tags: list[str],
    ) -> str:
        _ = (model, messages, temperature, tags)
        return JudgeOutput(
            overall_score=8.0, layer_scores=[], critical_issues=[], passed=True,
            rationale="ok", teacher_facing_summary="ok",
        ).model_dump_json()

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    artifact = _make_artifact("art-002", "quiz")
    store, references = await _persist_artifacts("run-test-002", [artifact])
    state = {"run_id": "run-test-002", "artifact_references": references}
    result = await render_quality(state, quality_gate=None, content_store=store)

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

    store, references = await _persist_artifacts("run-test-003", [artifact])
    state = {"run_id": "run-test-003", "artifact_references": references}
    result = await render_quality(state, quality_gate=mock_gate, content_store=store)

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
        "artifact_references": [
            {"document_id": "gen:art-004", "artifact_id": "art-004", "artifact_type": "lesson",
             "generation_id": "gen", "version": 1, "title": "Test Lesson"},
        ],
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


def test_gate_body_handles_escalated_state_without_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.agents.teaching_pack.nodes import _teacher_approval

    captured: list[dict[str, Any]] = []

    def fake_interrupt(payload: dict[str, Any]) -> dict[str, str]:
        captured.append(payload)
        return {"action": "reject", "feedback": "Needs repair"}

    monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

    state = {
        "run_id": "run-escalated-no-snapshots",
        "artifact_references": [
            {"document_id": "gen:art-escalated", "artifact_id": "art-escalated",
             "artifact_type": "lesson", "generation_id": "gen", "version": 1,
             "title": "Escalated Lesson"},
        ],
        "rendered_snapshots": None,
        "quality_scores": {"overall": 4.0, "passed": False},
        "escalate": True,
        "escalate_reason": "Quality checks did not pass.",
        "healing_strategy": "escalate",
        "fail_count": 4,
    }

    result = _teacher_approval(state)

    assert result["teacher_approved"] is False
    assert captured[0]["snapshot_ids"] == []
    assert captured[0]["rendered_snapshots"] == []
    assert captured[0]["escalated"] is True


def test_compliance_allows_trusted_research_source_urls_in_metadata() -> None:
    artifact = _make_artifact("art-cited")
    artifact["metadata"] = {
        "research_sources": [{
            "title": "ESL food vocabulary",
            "content": "Food vocabulary is common ESL content.",
            "url": "https://example.org/esl-food-vocabulary",
        }],
    }

    result = evaluate_compliance({"run_id": "run-cited", "artifacts": [artifact]})

    assert result.passed is True


def test_compliance_blocks_visible_student_url_content() -> None:
    artifact = _make_artifact("art-visible-url")
    artifact["sections"][0]["text"] = "Student should visit https://example.org/private-workspace."

    result = evaluate_compliance({"run_id": "run-visible-url", "artifacts": [artifact]})

    assert result.passed is False
    assert result.violations[0].code == "pii_leakage"
