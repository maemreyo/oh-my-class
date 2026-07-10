"""Teacher-visible Decision Provenance (ADR-055).

The schema is deliberately closed (`extra="forbid"`, a fixed field set with
no free-form/dict passthrough) so "excludes raw prompts and hidden
reasoning" is a property of the contract, not a rule a caller has to
remember to enforce -- there is no field anywhere in this model a raw
prompt or chain-of-thought string could be smuggled into.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.artifact_document import DocumentAuthority  # noqa: TC001
from common.contracts.claim_evidence import ClaimEvidence  # noqa: TC001


class DecisionProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1, max_length=80)
    version: int = Field(ge=1)
    authority: DocumentAuthority
    claim_evidence: list[ClaimEvidence] = Field(default_factory=list)
    dependency_document_ids: list[str] = Field(default_factory=list)
