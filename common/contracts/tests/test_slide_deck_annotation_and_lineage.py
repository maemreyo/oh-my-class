from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.slide_deck import (
    SlideDeckAnnotationOverlay,
    SlideDeckDisplayPreferences,
    SlideDeckManualEditAuthority,
    SlideDeckSnapshotLineage,
)


def test_annotation_overlay_defaults_to_teacher_only() -> None:
    overlay = SlideDeckAnnotationOverlay(
        target_slide_id="slide-1",
        created_from_snapshot_id="snap-abc123",
        content="Remind class about denominators here.",
    )

    assert overlay.teacher_only is True
    assert overlay.target_block_id is None


def test_annotation_overlay_keys_to_slide_and_block_ids() -> None:
    overlay = SlideDeckAnnotationOverlay(
        target_slide_id="slide-1",
        target_block_id="block-2",
        created_from_snapshot_id="snap-abc123",
        content="Highlight this example.",
        teacher_only=False,  # explicit future live-session action
    )

    assert overlay.target_block_id == "block-2"
    assert overlay.teacher_only is False


def test_annotation_overlay_requires_content_and_snapshot_ref() -> None:
    with pytest.raises(ValidationError):
        SlideDeckAnnotationOverlay(target_slide_id="slide-1", created_from_snapshot_id="snap-1", content="")


def test_snapshot_lineage_original_snapshot_has_no_parent_and_no_revalidation() -> None:
    lineage = SlideDeckSnapshotLineage()

    assert lineage.remix_of_snapshot_id is None
    assert lineage.requires_revalidation is False


def test_snapshot_lineage_remix_references_parent_and_requires_revalidation() -> None:
    lineage = SlideDeckSnapshotLineage(remix_of_snapshot_id="snap-parent-1")

    assert lineage.remix_of_snapshot_id == "snap-parent-1"
    assert lineage.requires_revalidation is True


def test_manual_edit_authority_excludes_arbitrary_markup() -> None:
    # ADR-045 decision 10: only these two values are ever valid. Anything
    # resembling raw HTML/CSS/JS must fail typed construction elsewhere.
    assert set(SlideDeckManualEditAuthority.__args__) == {"structured_patch", "regeneration_target"}


def test_lineage_and_display_preferences_do_not_share_a_field_namespace() -> None:
    # SDTF-06 AC: display preferences/export attempts are a separate concern
    # from content version lineage -- guard against future conflation by
    # keeping the two models' field sets disjoint.
    lineage_fields = set(SlideDeckSnapshotLineage.model_fields)
    display_fields = set(SlideDeckDisplayPreferences.model_fields)

    assert lineage_fields.isdisjoint(display_fields)
