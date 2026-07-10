"""Capability-checked export creation and explicit regeneration (ADR-056, ADR-058).

The single chokepoint every export write must go through: unsupported
(artifact_type, export_format) pairs fail here, before any file is written,
rather than at whatever renderer happens to notice later.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from common.contracts.teaching_pack_capabilities import (
    TeachingPackCapabilityManifest,
    is_export_pair_supported,
    load_teaching_pack_capabilities,
)
from services.gateway.teaching_pack_export_store import (
    ExportRecordCreate,
    ExportRecordRead,
    TeachingPackExportStore,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_snapshot_schemas import ArtifactSnapshotRead
    from services.gateway.teaching_pack_types import RunId


class UnsupportedExportPairError(ValueError):
    def __init__(self, artifact_type: str, export_format: str) -> None:
        self.artifact_type = artifact_type
        self.export_format = export_format
        super().__init__(
            f"{export_format!r} export is not supported for artifact type {artifact_type!r}",
        )


class ExportFormatNotImplementedError(NotImplementedError):
    """Raised for a format the capability manifest declares product-level support
    for, but that no writer can actually produce yet (see #453-458) -- never
    silently written as mislabeled HTML."""

    def __init__(self, export_format: str) -> None:
        self.export_format = export_format
        super().__init__(f"no writer implementation exists yet for {export_format!r}")


class RegenerateResult:
    __slots__ = ("regenerated", "reused")

    def __init__(self, regenerated: list[str], reused: list[str]) -> None:
        self.regenerated = regenerated
        self.reused = reused


def assert_export_pair_supported(
    manifest: TeachingPackCapabilityManifest, artifact_type: str, export_format: str,
) -> None:
    if not is_export_pair_supported(manifest, artifact_type, export_format):
        raise UnsupportedExportPairError(artifact_type, export_format)


async def create_export_record_checked(
    store: TeachingPackExportStore,
    manifest: TeachingPackCapabilityManifest,
    payload: ExportRecordCreate,
    artifact_type: str,
) -> ExportRecordRead:
    """Enforce the capability matrix, then persist with `capability_version` pinned.

    Callers must call this *before* writing the export file (fail before file
    creation) -- it does not itself guard the write, it is the guard.
    """
    assert_export_pair_supported(manifest, artifact_type, export_format=payload.format)
    stamped = ExportRecordCreate(
        export_id=payload.export_id,
        run_id=payload.run_id,
        artifact_id=payload.artifact_id,
        snapshot_id=payload.snapshot_id,
        format=payload.format,
        storage_path=payload.storage_path,
        capability_version=manifest.manifest_version,
    )
    return await store.create_export_record(stamped)


async def regenerate_stale_exports(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_id: str,
    artifact_type: str,
    head: ArtifactSnapshotRead,
    formats: list[str],
    manifest: TeachingPackCapabilityManifest | None = None,
    base_dir: Path = Path(".scratch/pipeline-v2/artifacts/exports"),
) -> RegenerateResult:
    """Regenerate only the `formats` that need it and reuse the rest untouched
    (ADR-056: "regeneration reuses unaffected outputs and creates immutable
    records" for the affected ones only).

    "Needs it" means stale *or* never exported at all -- a format with no
    prior export has nothing to reuse, so it is not "reused" just because it
    happens not to be stale; it goes through the same capability check as a
    genuinely stale format.

    Only `html` renders anything real today (the writer has no other format
    yet, per #453-458) -- other requested formats simply fail the capability
    check below rather than being silently skipped.
    """
    manifest = manifest or load_teaching_pack_capabilities()
    store = TeachingPackExportStore(session)
    needs_generation: list[str] = []
    reused: list[str] = []
    for export_format in formats:
        latest = await store.get_latest_export_for_format(run_id, artifact_id, export_format)
        if latest is not None and latest.snapshot_id == head.snapshot_id:
            reused.append(export_format)
        else:
            needs_generation.append(export_format)
    for export_format in needs_generation:
        assert_export_pair_supported(manifest, artifact_type, export_format)
        if export_format != "html":
            raise ExportFormatNotImplementedError(export_format)
        export_dir = base_dir / str(run_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{head.snapshot_id}.{export_format}"
        export_path.write_text(head.rendered_html, encoding="utf-8")
        await create_export_record_checked(
            store,
            manifest,
            ExportRecordCreate(
                export_id=f"export-{uuid4()}",
                run_id=run_id,
                artifact_id=artifact_id,
                snapshot_id=head.snapshot_id,
                format=export_format,
                storage_path=str(export_path),
            ),
            artifact_type,
        )
    return RegenerateResult(regenerated=needs_generation, reused=reused)
