"""Integration: the lesson_plan -> Layer-2 pedagogical seam (Phase 1, task 4d).

Before this fix the gate passed no lesson_plan, so prompt-alignment/Bloom/readability
silently auto-passed. These tests drive the REAL gate and prove prompt-alignment now
actually measures: content that ignores the planned objectives is flagged, and with no
pedagogy context the metric still auto-passes (documenting the pre-fix behaviour).
"""

from __future__ import annotations

import pytest

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import QualityFailureClass
from services.gateway.teaching_pack_quality_gate import GatewayTeachingPackQualityGate


def _workflow_state() -> ArtifactWorkflowState:
    return ArtifactWorkflowState(
        workflow_id="workflow-lesson-1",
        run_id="run-pedagogy-seam",
        artifact_id="lesson-1",
        artifact_type="lesson",
        status="validating",
        attempts=0,
        contract_revision_id=1,
        research_guidance_id="pedagogy-seam-test",
    )


def _artifact(*, with_context: bool) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if with_context:
        # Objectives about the water cycle; content below is about photosynthesis, so
        # the content does NOT reference the objectives -> prompt_alignment must fail.
        metadata["pedagogy_context"] = {"learning_objectives": ["Describe the water cycle"]}
    return {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Photosynthesis Lesson",
        "sections": [{"title": "Intro", "content": "Plants use sunlight to make energy."}],
        "metadata": metadata,
        "accessibility": {"language": "en"},
    }


def _prompt_alignment_issues(report: object) -> list[object]:
    return [
        issue
        for issue in report.issues  # type: ignore[attr-defined]
        if issue.failure_class is QualityFailureClass.PEDAGOGICAL_MISMATCH
        and issue.message.startswith("prompt_alignment")
    ]


@pytest.mark.anyio
async def test_pedagogical_measures_alignment_when_context_present() -> None:
    report = await GatewayTeachingPackQualityGate().evaluate(
        _workflow_state(), _artifact(with_context=True)
    )
    assert _prompt_alignment_issues(report), (
        "content ignores the planned objectives — prompt_alignment should now flag it"
    )


@pytest.mark.anyio
async def test_pedagogical_auto_passes_without_context() -> None:
    """Pre-fix behaviour, documented: no lesson_plan -> prompt_alignment cannot measure."""
    report = await GatewayTeachingPackQualityGate().evaluate(
        _workflow_state(), _artifact(with_context=False)
    )
    assert not _prompt_alignment_issues(report)
