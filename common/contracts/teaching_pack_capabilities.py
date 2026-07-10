"""Versioned product-truth capability manifest for the teaching-pack surface."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Literal, assert_never, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from common.contracts.artifact_document import ArtifactDocumentType
from common.contracts.run_contract import ExportFormat


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    DEGRADED = "degraded"
    REJECTED = "rejected"


class ArtifactCapability(BaseModel):
    """Declared support and constraints for one V2 artifact surface."""

    model_config = ConfigDict(frozen=True)

    artifact_type: ArtifactDocumentType
    status: CapabilityStatus
    payload_type: Literal["block_document", "assessment_document", "slide_deck_data"]
    renderer_plugin: str | None = None
    specialist_adapter: str | None = None
    audiences: tuple[Literal["student", "teacher", "print"], ...] = Field(min_length=1)
    supports_print: bool
    accessibility_requirements: tuple[str, ...] = Field(min_length=1)
    requires_answer_set: bool
    asset_policy: Literal["inline_only", "governed_media", "not_applicable"]
    degradation: str | None = None
    rejection_reason: str | None = None
    alternative: str | None = None

    @model_validator(mode="after")
    def _validate_status_requirements(self) -> ArtifactCapability:
        match self.status:
            case CapabilityStatus.SUPPORTED:
                if self.renderer_plugin is None or self.specialist_adapter is None:
                    raise PydanticCustomError(
                        "supported_adapter_required",
                        "supported artifacts require renderer and specialist adapters",
                    )
            case CapabilityStatus.DEGRADED:
                if self.renderer_plugin is None or self.specialist_adapter is None or self.degradation is None:
                    raise PydanticCustomError(
                        "degraded_adapter_required",
                        "degraded artifacts require adapters and a degradation declaration",
                    )
            case CapabilityStatus.REJECTED:
                if self.rejection_reason is None or self.alternative is None:
                    raise PydanticCustomError(
                        "rejection_details_required",
                        "rejected artifacts require a reason and alternative",
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class ExportCapability(BaseModel):
    """Declared support and constraints for one offline export format."""

    model_config = ConfigDict(frozen=True)

    export_format: ExportFormat
    status: CapabilityStatus
    supported_artifact_types: tuple[ArtifactDocumentType, ...]
    requires_answer_set: bool
    file_validation: str
    degradation: str | None = None
    rejection_reason: str | None = None
    alternative: str | None = None

    @model_validator(mode="after")
    def _validate_status_requirements(self) -> ExportCapability:
        match self.status:
            case CapabilityStatus.SUPPORTED:
                if not self.supported_artifact_types:
                    raise PydanticCustomError(
                        "supported_export_sources_required",
                        "supported exports require source artifacts",
                    )
            case CapabilityStatus.DEGRADED:
                if not self.supported_artifact_types or self.degradation is None:
                    raise PydanticCustomError(
                        "degraded_export_details_required",
                        "degraded exports require source artifacts and a degradation declaration",
                    )
            case CapabilityStatus.REJECTED:
                if self.rejection_reason is None or self.alternative is None:
                    raise PydanticCustomError(
                        "rejected_export_details_required",
                        "rejected exports require a reason and alternative",
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class TeachingPackCapabilityManifest(BaseModel):
    """One versioned declaration of renderer, specialist, and export truth."""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = Field(min_length=1)
    generated_from: str = Field(min_length=1)
    renderer_plugins: tuple[str, ...] = Field(min_length=1)
    specialist_adapters: tuple[str, ...] = Field(min_length=1)
    artifacts: tuple[ArtifactCapability, ...] = Field(min_length=1)
    exports: tuple[ExportCapability, ...] = Field(min_length=1)


class CapabilityManifestValidationError(ValueError):
    """Raised when a capability manifest omits a canonical product surface."""

    def __init__(
        self,
        missing_artifacts: set[str],
        missing_exports: set[str],
        duplicate_artifacts: set[str],
        duplicate_exports: set[str],
        undeclared_renderers: set[str],
        undeclared_specialists: set[str],
    ) -> None:
        self.missing_artifacts = missing_artifacts
        self.missing_exports = missing_exports
        self.duplicate_artifacts = duplicate_artifacts
        self.duplicate_exports = duplicate_exports
        self.undeclared_renderers = undeclared_renderers
        self.undeclared_specialists = undeclared_specialists
        super().__init__(
            "missing "
            f"artifacts={sorted(missing_artifacts)} exports={sorted(missing_exports)} "
            "duplicate "
            f"artifacts={sorted(duplicate_artifacts)} exports={sorted(duplicate_exports)} "
            "undeclared "
            f"renderers={sorted(undeclared_renderers)} specialists={sorted(undeclared_specialists)}",
        )


def load_teaching_pack_capabilities(
    path: Path | None = None,
) -> TeachingPackCapabilityManifest:
    """Parse the repository-owned manifest at the cross-package capability boundary."""
    manifest_path = path or _default_manifest_path()
    return TeachingPackCapabilityManifest.model_validate_json(manifest_path.read_text())


def validate_teaching_pack_capabilities(manifest: TeachingPackCapabilityManifest) -> None:
    """Fail closed when a canonical V2 artifact or export lacks a declaration."""
    expected_artifacts = set(get_args(ArtifactDocumentType))
    expected_exports = set(get_args(ExportFormat))
    declared_artifacts = {entry.artifact_type for entry in manifest.artifacts}
    declared_exports = {entry.export_format for entry in manifest.exports}
    missing_artifacts = expected_artifacts - declared_artifacts
    missing_exports = expected_exports - declared_exports
    duplicate_artifacts = _duplicates(entry.artifact_type for entry in manifest.artifacts)
    duplicate_exports = _duplicates(entry.export_format for entry in manifest.exports)
    declared_renderers = set(manifest.renderer_plugins)
    declared_specialists = set(manifest.specialist_adapters)
    undeclared_renderers = {
        entry.renderer_plugin
        for entry in manifest.artifacts
        if entry.renderer_plugin is not None and entry.renderer_plugin not in declared_renderers
    }
    undeclared_specialists = {
        entry.specialist_adapter
        for entry in manifest.artifacts
        if entry.specialist_adapter is not None and entry.specialist_adapter not in declared_specialists
    }
    if (
        missing_artifacts
        or missing_exports
        or duplicate_artifacts
        or duplicate_exports
        or undeclared_renderers
        or undeclared_specialists
    ):
        raise CapabilityManifestValidationError(
            missing_artifacts,
            missing_exports,
            duplicate_artifacts,
            duplicate_exports,
            undeclared_renderers,
            undeclared_specialists,
        )


def is_export_pair_supported(
    manifest: TeachingPackCapabilityManifest,
    artifact_type: str,
    export_format: str,
) -> bool:
    """True iff (artifact_type, export_format) is a declared, non-rejected pair.

    The one place that answers "can this artifact export to this format" --
    callers must not re-derive it from the raw manifest lists themselves.
    """
    capability = next((e for e in manifest.exports if e.export_format == export_format), None)
    if capability is None or capability.status is CapabilityStatus.REJECTED:
        return False
    return artifact_type in capability.supported_artifact_types


def _default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "common" / "component_strategy_knowledge" / "capabilities" / "teaching_pack.json"


def _duplicates(values: Iterable[str]) -> set[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return {value for value, count in counts.items() if count > 1}
