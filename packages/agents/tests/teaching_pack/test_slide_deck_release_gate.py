from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.quality import ArtifactQualityReport
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
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
    _ = stub_section_prose
    content_store = InMemoryArtifactContentStore()
    slide_result = await generate_one_artifact({
        "run_id": "run-slide-release",
        "artifact_generation_id": "run-slide-release:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "dependency_artifact_references": [],
    }, content_store)
    slide_reference = slide_result["artifact_references"][0]
    slide_deck = (await content_store.read_projection(slide_reference["document_id"])).model_dump(mode="json")
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
    lesson_reference = await content_store.persist(
        "run-slide-release",
        "run-slide-release:artifact:1",
        ArtifactContent.model_validate(lesson),
        "lesson-1",
    )
    quiz_reference = await content_store.persist(
        "run-slide-release",
        "run-slide-release:artifact:1",
        ArtifactContent.model_validate(quiz),
        "quiz-1",
    )

    quality = await render_quality({
        "run_id": "run-slide-release",
        "artifact_references": [lesson_reference.as_state(), slide_reference, quiz_reference.as_state()],
    }, quality_gate=PassingQualityGate(), content_store=content_store)

    snapshots = quality["rendered_snapshots"]
    snapshot_types = {snapshot["artifact_type"] for snapshot in snapshots}

    assert slide_deck["artifact_type"] == "slide_deck"
    assert slide_result["artifact_workflow_states"][0]["status"] == "passed"
    assert snapshot_types == {"lesson", "slide_deck", "quiz"}
    assert quality["quality_scores"]["passed"] is True
    assert quality["quality_scores"]["snapshot_count"] == 3


@pytest.mark.anyio
async def test_slide_deck_generation_bypasses_content_creator_node(monkeypatch: pytest.MonkeyPatch, stub_section_prose) -> None:
    _ = stub_section_prose

    async def fail_if_called(_state: dict[str, object]) -> dict[str, object]:
        raise AssertionError("slide deck must use SlideDeckEngine dispatch")

    monkeypatch.setattr(
        "packages.agents.teaching_pack.generate_one_artifact.content_creator_node",
        fail_if_called,
    )
    result = await generate_one_artifact({
        "run_id": "run-slide-dispatch",
        "artifact_generation_id": "run-slide-dispatch:artifact:1",
        "artifact_type": "slide_deck",
        "lesson_plan": _lesson_plan(),
        "research_brief": _research_brief(),
        "theme": "default",
        "dependency_artifact_references": [],
    }, InMemoryArtifactContentStore())

    assert result["artifact_workflow_states"][0]["status"] == "passed"
