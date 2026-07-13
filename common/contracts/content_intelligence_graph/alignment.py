"""#465 (Content Intelligence Graph): curriculum alignment records.

The issue's Acceptance Criteria: "Every claimed curriculum alignment
resolves to a versioned source node and evidence record." `CurriculumStandard`
(`subject_capability_pack.py`) is the versioned source node; `ClaimEvidence`
(`claim_evidence.py`, ADR-054) is the evidence record. Neither was ever
connected to a knowledge component by a typed record -- an alignment claim
lived only as prose inside prompts/skills. `CurriculumAlignmentRecord` is
that missing link, reusing both existing contracts rather than duplicating
either.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.claim_evidence import ClaimEvidence, assert_high_risk_claims_are_grounded
from common.contracts.subject_capability_pack import CurriculumStandard


class CurriculumAlignmentError(ValueError):
    """Base class for defects in a curriculum alignment claim."""


class CurriculumAlignmentUngroundedError(CurriculumAlignmentError):
    """Fail-closed (ADR-054): a `high`-risk alignment claim lacks grounded
    evidence -- the caller must not silently treat the alignment as certified."""

    def __init__(self, knowledge_component_id: str, standard_code: str, reason: str) -> None:
        self.knowledge_component_id = knowledge_component_id
        self.standard_code = standard_code
        self.reason = reason
        super().__init__(
            f"alignment of {knowledge_component_id!r} to {standard_code!r} failed grounding check: {reason}",
        )


class CurriculumAlignmentRecord(BaseModel):
    """One claimed alignment: this knowledge component satisfies this
    versioned curriculum standard, substantiated by this evidence."""

    model_config = ConfigDict(frozen=True)

    knowledge_component_id: str = Field(min_length=1, max_length=80)
    standard: CurriculumStandard
    evidence: ClaimEvidence


def assert_alignment_is_grounded(record: CurriculumAlignmentRecord) -> None:
    """Fail closed (same ADR-054 rule as `assert_high_risk_claims_are_grounded`)
    when a `high`-risk alignment claim isn't citable and verified -- raises
    `CurriculumAlignmentUngroundedError` instead of letting an unsubstantiated
    "certified" claim reach a specialist or a teacher-visible artifact.
    """
    failures = assert_high_risk_claims_are_grounded([record.evidence])
    if failures:
        raise CurriculumAlignmentUngroundedError(
            record.knowledge_component_id, record.standard.code, failures[0].reason,
        )
