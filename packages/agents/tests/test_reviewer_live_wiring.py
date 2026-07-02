from __future__ import annotations

from packages.agents.teaching_pack.quality_runtime import render_quality


async def test_render_quality_invokes_reviewer_layer4_by_default() -> None:
    result = await render_quality({
        "run_id": "run-reviewer-live",
        "artifacts": [_artifact("Explain equivalent fractions clearly.")],
    })

    quality_scores = result["quality_scores"]

    assert quality_scores["passed"] is True
    assert quality_scores["layer4_reviewer"]["judge_count"] >= 2
    assert quality_scores["layer4_reviewer"]["inter_rater_agreement"] >= 0.5


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
