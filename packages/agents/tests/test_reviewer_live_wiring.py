from __future__ import annotations

import pytest

from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.agents.teaching_pack.quality_runtime import render_quality


async def test_render_quality_invokes_reviewer_layer4_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """LIC-01: format/PII pre-filter (LiveReviewerQualityGate) passes, then
    AdaptiveJudge (reviewer_node) becomes the real content/pedagogy/presentation
    gate — `layer4_reviewer` now holds its output, not the heuristic's."""
    from packages.agents import llm

    async def fake_complete_json_chat(*, model: str, messages: list, temperature: float, tags: list[str]) -> str:
        return JudgeOutput(
            overall_score=8.0,
            layer_scores=[LayerScore(layer="content_quality", score=8.0, weight=1.0)],
            critical_issues=[],
            passed=True,
            rationale="Meets rubric.",
            teacher_facing_summary="Ready for teacher review.",
        ).model_dump_json()

    monkeypatch.setattr(llm, "complete_json_chat", fake_complete_json_chat)

    result = await render_quality({
        "run_id": "run-reviewer-live",
        "artifacts": [_artifact("Explain equivalent fractions clearly.")],
    })

    quality_scores = result["quality_scores"]

    assert quality_scores["passed"] is True
    assert quality_scores["layer4_reviewer"]["passed"] is True
    assert quality_scores["layer4_reviewer"]["teacher_facing_summary"] == "Ready for teacher review."


async def test_reviewer_layer4_fails_missing_objective_with_evidence() -> None:
    result = await render_quality({
        "run_id": "run-reviewer-objective",
        "artifacts": [_artifact("This only discusses classroom routines.")],
    })

    assert result["quality_recovery_route"] == "planning_blueprint"
    assert any("missing objective" in issue for issue in result["quality_issues"])
    assert result["quality_scores"]["passed"] is False


async def test_reviewer_layer4_escalates_low_inter_rater_agreement() -> None:
    result = await render_quality({
        "run_id": "run-reviewer-disagree",
        "artifacts": [_artifact("Explain equivalent fractions clearly.", force_disagreement=True)],
    })

    assert result["quality_recovery_route"] == "artifact_workflow"
    assert any("low_agreement" in issue for issue in result["quality_issues"])


def test_reviewer_calibration_shifts_threshold_after_teacher_disagreement() -> None:
    from packages.agents.sub_agents.reviewer.live_quality_gate import ReviewerCalibration

    calibration = ReviewerCalibration()
    before = calibration.threshold

    calibration.record(judge_passed=True, teacher_approved=False, effectiveness=0.3)

    assert calibration.threshold > before


def _artifact(content: str, *, force_disagreement: bool = False) -> dict[str, object]:
    return {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Equivalent Fractions Lesson",
        "sections": [{"title": "Explain", "content": content}],
        "metadata": {
            "pedagogy_context": {
                "learning_objectives": [
                    {"description": "Explain equivalent fractions", "bloom_level": "understand"},
                ],
            },
            "research_sources": [
                {"title": "Verified", "content": "Equivalent fractions represent the same value."},
                {"title": "Verified 2", "content": "Equivalent fractions can use different numerators and denominators."},
            ],
            "force_reviewer_disagreement": force_disagreement,
        },
        "accessibility": {"language": "en"},
    }
