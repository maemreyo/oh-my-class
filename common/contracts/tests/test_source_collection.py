from __future__ import annotations

from common.contracts.source_collection import (
    SourceCollection,
    SourceCollectionEntry,
    VerifiedFinding,
    detect_required_source_conflicts,
)


def _collection(**entry_overrides: object) -> SourceCollection:
    defaults: dict[str, object] = {
        "entry_id": "entry-1",
        "title": "District science handbook",
        "authority": "required",
        "subject_key": "boiling_point_water_celsius",
        "claim_value": "100",
    }
    defaults.update(entry_overrides)
    return SourceCollection(
        collection_id="sources-1",
        scope="private_teacher",
        owner_id="teacher-1",
        entries=[SourceCollectionEntry(**defaults)],
    )


def test_required_source_conflicting_with_verified_finding_is_reported() -> None:
    collection = _collection()
    findings = [VerifiedFinding(
        subject_key="boiling_point_water_celsius",
        claim_value="90",
        source_id="src-verified-1",
        verification_status="VERIFIED",
    )]

    conflicts = detect_required_source_conflicts(collection, findings)

    assert len(conflicts) == 1
    assert conflicts[0].entry_id == "entry-1"
    assert conflicts[0].required_claim_value == "100"
    assert conflicts[0].verified_claim_value == "90"
    assert conflicts[0].verified_source_id == "src-verified-1"


def test_matching_claim_value_is_not_a_conflict() -> None:
    collection = _collection()
    findings = [VerifiedFinding(
        subject_key="boiling_point_water_celsius",
        claim_value="100",
        source_id="src-verified-1",
        verification_status="VERIFIED",
    )]

    assert detect_required_source_conflicts(collection, findings) == []


def test_uncertain_finding_never_overrides_a_required_source() -> None:
    collection = _collection()
    findings = [VerifiedFinding(
        subject_key="boiling_point_water_celsius",
        claim_value="90",
        source_id="src-uncertain-1",
        verification_status="UNCERTAIN",
    )]

    assert detect_required_source_conflicts(collection, findings) == []


def test_preferred_authority_never_conflicts() -> None:
    collection = _collection(authority="preferred")
    findings = [VerifiedFinding(
        subject_key="boiling_point_water_celsius",
        claim_value="90",
        source_id="src-verified-1",
        verification_status="VERIFIED",
    )]

    assert detect_required_source_conflicts(collection, findings) == []


def test_different_subject_key_never_conflicts() -> None:
    collection = _collection()
    findings = [VerifiedFinding(
        subject_key="freezing_point_water_celsius",
        claim_value="0",
        source_id="src-verified-1",
        verification_status="VERIFIED",
    )]

    assert detect_required_source_conflicts(collection, findings) == []
