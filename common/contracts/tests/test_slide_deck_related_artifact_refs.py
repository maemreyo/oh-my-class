from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.slide_deck import (
    SlideDeckData,
    SlideDeckRelatedArtifactRef,
    resolve_slide_deck_related_refs,
)
from common.contracts.tests.test_slide_deck import _valid_deck


def test_related_ref_is_a_pointer_not_embedded_content() -> None:
    ref = SlideDeckRelatedArtifactRef(
        artifact_type="worksheet",
        artifact_id="worksheet-2",
        relationship_label="See Worksheet 2",
    )

    assert ref.artifact_id == "worksheet-2"
    assert ref.relationship_label == "See Worksheet 2"
    # A pointer, not embedded content: no field exists to carry worksheet
    # body/answer-key text.
    assert "content" not in SlideDeckRelatedArtifactRef.model_fields
    assert "answer" not in " ".join(SlideDeckRelatedArtifactRef.model_fields).lower()


def test_related_ref_accepts_objective_and_checkpoint_semantic_targets() -> None:
    objective_ref = SlideDeckRelatedArtifactRef(
        artifact_type="objective", artifact_id="obj-3", relationship_label="Builds on Objective 3",
    )
    checkpoint_ref = SlideDeckRelatedArtifactRef(
        artifact_type="checkpoint", artifact_id="checkpoint-exit-1", relationship_label="Feeds the exit checkpoint",
    )

    assert objective_ref.artifact_type == "objective"
    assert checkpoint_ref.artifact_type == "checkpoint"


def test_related_ref_rejects_unknown_artifact_type() -> None:
    with pytest.raises(ValidationError):
        SlideDeckRelatedArtifactRef(
            artifact_type="not_a_real_type",  # type: ignore[arg-type]
            artifact_id="x",
            relationship_label="See X",
        )


def test_related_ref_rejects_missing_id_or_label() -> None:
    with pytest.raises(ValidationError):
        SlideDeckRelatedArtifactRef(artifact_type="quiz", artifact_id="", relationship_label="See Quiz")

    with pytest.raises(ValidationError):
        SlideDeckRelatedArtifactRef(artifact_type="quiz", artifact_id="quiz-1", relationship_label="")


def test_slide_and_block_metadata_can_carry_related_refs() -> None:
    payload = _valid_deck()
    payload["slides"][0]["related_refs"] = [
        {"artifact_type": "objective", "artifact_id": "obj-1", "relationship_label": "Supports Objective 1"},
    ]
    payload["slides"][0]["blocks"][0]["related_refs"] = [
        {"artifact_type": "worksheet", "artifact_id": "worksheet-2", "relationship_label": "See Worksheet 2"},
    ]

    deck = SlideDeckData.model_validate(payload)

    assert deck.slides[0].related_refs[0].artifact_id == "obj-1"
    assert deck.slides[0].blocks[0].related_refs[0].relationship_label == "See Worksheet 2"


def test_deck_without_related_refs_still_validates() -> None:
    # Foundation default: existing decks with no related_refs field at all
    # keep validating unchanged.
    deck = SlideDeckData.model_validate(_valid_deck())

    assert deck.slides[0].related_refs == []
    assert deck.slides[0].blocks[0].related_refs == []


def test_deck_with_dangling_related_ref_still_exports_standalone() -> None:
    # SDTF-03 AC: a referenced artifact_id missing from the run's artifact
    # list must never break standalone deck construction/export.
    payload = _valid_deck()
    payload["slides"][0]["related_refs"] = [
        {"artifact_type": "quiz", "artifact_id": "quiz-does-not-exist", "relationship_label": "See the practice quiz"},
    ]

    deck = SlideDeckData.model_validate(payload)  # does not raise

    assert deck.slides[0].related_refs[0].artifact_id == "quiz-does-not-exist"


def test_resolve_related_refs_flags_missing_artifacts_without_raising() -> None:
    refs = [
        SlideDeckRelatedArtifactRef(artifact_type="quiz", artifact_id="quiz-1", relationship_label="See Quiz 1"),
        SlideDeckRelatedArtifactRef(artifact_type="worksheet", artifact_id="worksheet-missing", relationship_label="See Worksheet"),
    ]

    statuses = resolve_slide_deck_related_refs(refs, known_artifact_ids={"quiz-1"})

    resolved_by_id = {status.ref.artifact_id: status.resolved for status in statuses}
    assert resolved_by_id == {"quiz-1": True, "worksheet-missing": False}


def test_resolve_related_refs_handles_empty_inputs() -> None:
    assert resolve_slide_deck_related_refs([], known_artifact_ids=set()) == []
