from __future__ import annotations

import pytest

from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.quality_runtime import render_quality


class PassingQualityGate:
    async def evaluate(self, state, _artifact):  # noqa: ANN001 - test seam mirrors QualityGate protocol
        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=True,
        )


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent fractions",
        "grade_level": "Grade 5",
        "learning_objectives": [
            {"description": "Explain why two fractions are equivalent."},
        ],
        "learning_plan": {"present_content": {}, "assess_performance": {}},
    }


def _research_brief() -> dict[str, object]:
    return {
        "sources": [
            {
                "id": "src-fractions-standard",
                "title": "Grade 5 Fractions Standard",
                "citation": "CCSS 5.NF.A",
                "excerpt": "Equivalent fractions name the same amount.",
            },
        ],
    }


@pytest.mark.anyio
async def test_slide_deck_release_gate_pipeline_produces_approval_snapshots(stub_section_prose) -> None:
    slide_result = await generate_one_artifact({
        "run_id": "run-slide-release",
        "artifact_generation_id": "run-slide-release:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "dependency_artifacts": [{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
    })
    slide_deck = slide_result["artifact_chunks"][0]
    lesson = {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Equivalent Fractions Lesson",
        "sections": [{"title": "Intro", "content": "Equivalent fractions name the same amount."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }
    quiz = {
        "artifact_id": "quiz-1",
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Equivalent Fractions Quiz",
        "sections": [{"title": "Check", "content": "Which fraction equals one half?"}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }

    quality = await render_quality({
        "run_id": "run-slide-release",
        "artifacts": [lesson, slide_deck, quiz],
    }, quality_gate=PassingQualityGate())

    snapshots = quality["rendered_snapshots"]
    snapshot_types = {snapshot["artifact_type"] for snapshot in snapshots}

    assert slide_deck["artifact_type"] == "slide_deck"
    assert slide_result["artifact_workflow_states"][0]["status"] == "passed"
    assert snapshot_types == {"lesson", "slide_deck", "quiz"}
    assert quality["quality_scores"]["passed"] is True
    assert quality["quality_scores"]["snapshot_count"] == 3
