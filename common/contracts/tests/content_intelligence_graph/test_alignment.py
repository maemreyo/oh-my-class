from __future__ import annotations

import pytest

from common.contracts.claim_evidence import ClaimEvidence
from common.contracts.content_intelligence_graph.alignment import (
    CurriculumAlignmentRecord,
    CurriculumAlignmentUngroundedError,
    assert_alignment_is_grounded,
)
from common.contracts.subject_capability_pack import CurriculumStandard


def _record(risk_level: str, citation_ids: list[str], verification_status: str) -> CurriculumAlignmentRecord:
    return CurriculumAlignmentRecord(
        knowledge_component_id="kc.1",
        standard=CurriculumStandard(
            framework="CCSS",
            code="CCSS.MATH.CONTENT.3.OA.A.1",
            description_en="en",
            description_vi="vi",
        ),
        evidence=ClaimEvidence(
            claim_id="claim.1",
            claim_text="text",
            risk_level=risk_level,
            citation_ids=citation_ids,
            verification_status=verification_status,
        ),
    )


def test_low_risk_alignment_without_citations_does_not_fail_closed() -> None:
    record = _record("low", [], "UNCERTAIN")
    assert_alignment_is_grounded(record)  # no raise


def test_high_risk_alignment_without_citations_fails_closed() -> None:
    record = _record("high", [], "VERIFIED")
    with pytest.raises(CurriculumAlignmentUngroundedError):
        assert_alignment_is_grounded(record)


def test_high_risk_alignment_unverified_fails_closed() -> None:
    record = _record("high", ["source.1"], "UNCERTAIN")
    with pytest.raises(CurriculumAlignmentUngroundedError):
        assert_alignment_is_grounded(record)


def test_high_risk_alignment_cited_and_verified_passes() -> None:
    record = _record("high", ["source.1"], "VERIFIED")
    assert_alignment_is_grounded(record)  # no raise


def test_alignment_record_is_frozen() -> None:
    record = _record("medium", ["source.1"], "VERIFIED")
    with pytest.raises(Exception):  # noqa: B017, PT011
        record.knowledge_component_id = "changed"  # type: ignore[misc]
