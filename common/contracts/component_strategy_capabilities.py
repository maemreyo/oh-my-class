from __future__ import annotations

import hashlib
from pathlib import Path

from common.contracts.component_strategy_knowledge_models import (
    ExporterCapabilityManifest,
    KnowledgeManifest,
    RendererCapabilityManifest,
)


class CapabilityValidationError(ValueError):
    pass


def capability_manifest_path(root: Path, kind: str) -> Path:
    return root / "common" / "component_strategy_knowledge" / "capabilities" / f"{kind}.json"


def load_renderer_capabilities(path: Path) -> RendererCapabilityManifest:
    return RendererCapabilityManifest.model_validate_json(path.read_text())


def load_exporter_capabilities(path: Path) -> ExporterCapabilityManifest:
    return ExporterCapabilityManifest.model_validate_json(path.read_text())


def validate_manifest_checksums(
    manifest: KnowledgeManifest,
    renderer_path: Path,
    exporter_path: Path,
) -> tuple[RendererCapabilityManifest, ExporterCapabilityManifest]:
    renderer = load_renderer_capabilities(renderer_path)
    exporter = load_exporter_capabilities(exporter_path)
    if manifest.renderer_capability_checksum != _sha256_bytes(renderer_path.read_bytes()):
        raise CapabilityValidationError("renderer capability checksum is stale")
    if manifest.exporter_capability_checksum != _sha256_bytes(exporter_path.read_bytes()):
        raise CapabilityValidationError("exporter capability checksum is stale")
    if manifest.manifest_checksum == "computed-at-build":
        raise CapabilityValidationError("knowledge manifest checksum is not pinned")
    if not renderer.components or not exporter.exporters:
        raise CapabilityValidationError("capability manifests must not be empty")
    return renderer, exporter


def require_renderer_capability(component_type: str, manifest: RendererCapabilityManifest) -> None:
    supported = {component.component_type for component in manifest.components}
    if component_type not in supported:
        raise CapabilityValidationError(f"unsupported renderer capability {component_type}")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
