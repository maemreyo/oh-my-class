from __future__ import annotations

import pytest

from common.contracts.teaching_pack_capabilities import (
    CapabilityManifestValidationError,
    CapabilityStatus,
    load_teaching_pack_capabilities,
    validate_teaching_pack_capabilities,
)


def test_manifest_declares_every_v2_artifact_and_export_format() -> None:
    manifest = load_teaching_pack_capabilities()

    validate_teaching_pack_capabilities(manifest)

    assert {entry.artifact_type for entry in manifest.artifacts} == {
        "lesson",
        "worksheet",
        "quiz",
        "drill",
        "recap",
        "infographic",
        "flashcard_deck",
        "answer_key",
        "roadmap",
        "slide_deck",
        "exit_ticket",
        "reading_passage",
    }
    assert {entry.export_format for entry in manifest.exports} == {
        "html",
        "gift",
        "h5p",
        "qti",
        "anki_apkg",
        "flashcard_tsv",
        "pptx",
    }


def test_manifest_makes_current_pipeline_gaps_explicit() -> None:
    manifest = load_teaching_pack_capabilities()
    capabilities = {entry.artifact_type: entry for entry in manifest.artifacts}
    exports = {entry.export_format: entry for entry in manifest.exports}

    assert capabilities["infographic"].status is CapabilityStatus.REJECTED
    assert capabilities["slide_deck"].specialist_adapter == "slide_deck_engine"
    assert capabilities["quiz"].requires_answer_set is True
    assert exports["qti"].status is CapabilityStatus.REJECTED
    assert exports["pptx"].supported_artifact_types == ("slide_deck",)


def test_manifest_rejects_duplicate_surface_declarations() -> None:
    manifest = load_teaching_pack_capabilities()
    duplicate = manifest.model_copy(update={"artifacts": (*manifest.artifacts, manifest.artifacts[0])})

    with pytest.raises(CapabilityManifestValidationError, match="duplicate"):
        validate_teaching_pack_capabilities(duplicate)


def test_manifest_rejects_undeclared_renderer_adapter() -> None:
    manifest = load_teaching_pack_capabilities()
    lesson = manifest.artifacts[0].model_copy(update={"renderer_plugin": "not-a-renderer"})
    invalid = manifest.model_copy(update={"artifacts": (lesson, *manifest.artifacts[1:])})

    with pytest.raises(CapabilityManifestValidationError, match="undeclared"):
        validate_teaching_pack_capabilities(invalid)


def test_manifest_rejects_missing_artifact_declaration() -> None:
    manifest = load_teaching_pack_capabilities()
    missing = manifest.model_copy(update={"artifacts": manifest.artifacts[1:]})

    with pytest.raises(CapabilityManifestValidationError, match="missing"):
        validate_teaching_pack_capabilities(missing)


def test_manifest_rejects_missing_export_declaration() -> None:
    manifest = load_teaching_pack_capabilities()
    missing = manifest.model_copy(update={"exports": manifest.exports[1:]})

    with pytest.raises(CapabilityManifestValidationError, match="missing"):
        validate_teaching_pack_capabilities(missing)
