from __future__ import annotations

from common.contracts.teaching_pack_capabilities import (
    ArtifactCapability,
    CapabilityStatus,
    ExportCapability,
    TeachingPackCapabilityManifest,
    is_export_pair_supported,
)


def _manifest(**export_overrides: object) -> TeachingPackCapabilityManifest:
    export_defaults: dict[str, object] = {
        "export_format": "html",
        "status": CapabilityStatus.SUPPORTED,
        "supported_artifact_types": ("lesson", "worksheet"),
        "requires_answer_set": False,
        "file_validation": "well-formed HTML",
    }
    export_defaults.update(export_overrides)
    return TeachingPackCapabilityManifest(
        manifest_version="v-test",
        generated_from="test",
        renderer_plugins=("renderer.html",),
        specialist_adapters=("specialist.lesson",),
        artifacts=(
            ArtifactCapability(
                artifact_type="lesson",
                status=CapabilityStatus.SUPPORTED,
                payload_type="block_document",
                renderer_plugin="renderer.html",
                specialist_adapter="specialist.lesson",
                audiences=("student",),
                supports_print=True,
                accessibility_requirements=("alt-text",),
                requires_answer_set=False,
                asset_policy="not_applicable",
            ),
        ),
        exports=(ExportCapability(**export_defaults),),
    )


def test_supported_pair_is_true() -> None:
    assert is_export_pair_supported(_manifest(), "lesson", "html") is True


def test_artifact_type_outside_the_declared_list_is_false() -> None:
    assert is_export_pair_supported(_manifest(), "quiz", "html") is False


def test_unknown_export_format_is_false() -> None:
    assert is_export_pair_supported(_manifest(), "lesson", "gift") is False


def test_rejected_export_format_is_false_even_if_listed() -> None:
    manifest = _manifest(
        status=CapabilityStatus.REJECTED,
        supported_artifact_types=(),
        rejection_reason="not implemented",
        alternative="use html",
    )
    assert is_export_pair_supported(manifest, "lesson", "html") is False
