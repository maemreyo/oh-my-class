"""Scoped Source Collections with authority levels and conflict detection (ADR-051, ADR-054)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceAuthority = Literal["required", "preferred", "reference"]
SourceCollectionScope = Literal["private_teacher", "organization", "system"]


class SourceCollectionEntry(BaseModel):
    """One teacher-owned source. `subject_key`/`claim_value` pin down the specific,
    checkable fact this source asserts (e.g. subject_key="boiling_point_water_celsius",
    claim_value="100") -- that structured pair, not the freeform excerpt, is what
    conflict detection compares against verified research evidence."""

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    authority: SourceAuthority
    url: str | None = Field(default=None, max_length=2_000)
    excerpt: str | None = Field(default=None, max_length=8_000)
    subject_key: str | None = Field(default=None, max_length=120)
    claim_value: str | None = Field(default=None, max_length=500)
    copyright_ack: bool = False


class SourceCollection(BaseModel):
    """A scoped, teacher-owned bundle of Source Collection entries."""

    model_config = ConfigDict(frozen=True)

    collection_id: str = Field(min_length=1, max_length=80)
    scope: SourceCollectionScope
    owner_id: str = Field(min_length=1, max_length=64)
    entries: list[SourceCollectionEntry] = Field(min_length=1)


class VerifiedFinding(BaseModel):
    """One deterministically verified research finding, for conflict comparison
    against a `required` Source Collection entry with the same `subject_key`."""

    model_config = ConfigDict(frozen=True)

    subject_key: str = Field(min_length=1, max_length=120)
    claim_value: str = Field(min_length=1, max_length=500)
    source_id: str = Field(min_length=1, max_length=64)
    verification_status: Literal["VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"]


class SourceConflict(BaseModel):
    """A material disagreement between a `required` source and verified evidence.

    Neither side auto-wins (ADR-054) -- this is teacher-visible input to the
    `source_conflict` Planning Review gate, not a resolution.
    """

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(min_length=1, max_length=80)
    subject_key: str = Field(min_length=1, max_length=120)
    required_claim_value: str = Field(min_length=1, max_length=500)
    verified_claim_value: str = Field(min_length=1, max_length=500)
    verified_source_id: str = Field(min_length=1, max_length=64)


def detect_required_source_conflicts(
    collection: SourceCollection,
    verified_findings: list[VerifiedFinding],
) -> list[SourceConflict]:
    """Material conflicts between `required` entries and verified evidence on the same claim.

    Deterministic by design (ADR-054's triangulation is code-derived, not an
    LLM judgment call): a conflict exists only when both sides pin down the
    *same* `subject_key` with a *different* `claim_value`, and the competing
    finding is itself `VERIFIED` -- an `UNCERTAIN` finding never overrides a
    teacher's required source.
    """
    verified_by_subject = {
        finding.subject_key: finding
        for finding in verified_findings
        if finding.verification_status == "VERIFIED"
    }
    conflicts: list[SourceConflict] = []
    for entry in collection.entries:
        if entry.authority != "required" or entry.subject_key is None or entry.claim_value is None:
            continue
        finding = verified_by_subject.get(entry.subject_key)
        if finding is None or finding.claim_value == entry.claim_value:
            continue
        conflicts.append(SourceConflict(
            entry_id=entry.entry_id,
            subject_key=entry.subject_key,
            required_claim_value=entry.claim_value,
            verified_claim_value=finding.claim_value,
            verified_source_id=finding.source_id,
        ))
    return conflicts
