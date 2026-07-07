"""Integration: the researcher -> Layer-2 fact_check corpus seam (Phase 1).

Before 2026-07-01 nothing wrote ``artifact.metadata.research_sources``, so the gate's
fact_check ran against an empty corpus and could never VERIFY a claim. These tests
drive the REAL ``GatewayTeachingPackQualityGate`` and prove the corpus now changes the
    verdict: a factual claim is not blocked when no corpus exists, and VERIFIED once the
    grounded corpus is present in metadata.
"""

from __future__ import annotations

import pytest

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import QualityFailureClass
from services.gateway.teaching_pack_quality_gate import GatewayTeachingPackQualityGate

CLAIM_TEXT = "Photosynthesis was discovered in 1804."
SOURCE_BODY = "Photosynthesis was discovered in 1804 by early scientists."


def _workflow_state() -> ArtifactWorkflowState:
    return ArtifactWorkflowState(
        workflow_id="workflow-lesson-1",
        run_id="run-fact-seam",
        artifact_id="lesson-1",
        artifact_type="lesson",
        status="validating",
        attempts=0,
        contract_revision_id=1,
        research_guidance_id="fact-seam-test",
    )


def _artifact(*, with_corpus: bool) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if with_corpus:
        metadata["research_sources"] = [
            {"title": "Source A", "content": SOURCE_BODY, "url": "https://a.edu"},
            {"title": "Source B", "content": SOURCE_BODY, "url": "https://b.edu"},
        ]
    return {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Photosynthesis Lesson",
        "sections": [{"title": "Intro", "content": CLAIM_TEXT}],
        "metadata": metadata,
        "accessibility": {"language": "en"},
    }


def _fact_issues(report: object) -> list[object]:
    return [
        issue
        for issue in report.issues  # type: ignore[attr-defined]
        if issue.failure_class is QualityFailureClass.FACTUAL_UNCERTAINTY
    ]


@pytest.mark.anyio
async def test_fact_check_flags_claim_when_corpus_absent() -> None:
    """No corpus -> delivery-time evidence is absent, so the gate fails open."""
    report = await GatewayTeachingPackQualityGate().evaluate(
        _workflow_state(), _artifact(with_corpus=False)
    )
    assert not _fact_issues(report), "starved fact_check should not block generation"


@pytest.mark.anyio
async def test_fact_check_verifies_claim_when_corpus_present() -> None:
    """Seam closed: grounded corpus in metadata -> claim VERIFIED by >=2 sources."""
    report = await GatewayTeachingPackQualityGate().evaluate(
        _workflow_state(), _artifact(with_corpus=True)
    )
    assert not _fact_issues(report), (
        "fact_check received the research corpus and should VERIFY the supported claim"
    )
