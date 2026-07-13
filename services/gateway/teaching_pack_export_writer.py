from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from services.gateway.teaching_pack_snapshot_validators import teacher_only_value_paths
from services.gateway.teaching_pack_types import JsonObject, RunId

if TYPE_CHECKING:
    from services.gateway.object_storage import ObjectStorageConfig, S3Client

type ExportFormat = Literal["html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "pptx", "google_forms"]

_EXPORT_CLI_PATH = Path("packages/exporters/dist/cli.js")
_EXPORT_CLI_TIMEOUT = 30.0


class ExportAdapterError(RuntimeError):
    def __init__(self, message: str, exit_code: int | None = None, stderr: str | None = None) -> None:
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(message)


class TeachingPackSnapshotRenderer(Protocol):
    async def render(self, artifact: JsonObject) -> str: ...


class TeachingPackExportWriter(Protocol):
    async def write_exports(self, run_id: RunId, state: JsonObject) -> list[str]: ...


class RendererAdapterSnapshotRenderer:
    async def render(self, artifact: JsonObject) -> str:
        from services.gateway.renderer_adapter import render_artifact_content

        return await render_artifact_content(artifact)


@dataclass(frozen=True, slots=True)
class FileSystemTeachingPackExportWriter:
    base_dir: Path = Path(".scratch/pipeline-v2/artifacts/exports")
    renderer: TeachingPackSnapshotRenderer = RendererAdapterSnapshotRenderer()

    async def write_exports(self, run_id: RunId, state: JsonObject) -> list[str]:
        export_dir = self.base_dir / str(run_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        unsupported_formats = _unsupported_formats(state)
        if unsupported_formats:
            raise ExportAdapterError(
                "Unsupported export format for offline gateway writer: "
                + ", ".join(unsupported_formats),
            )
        exported_files: list[str] = []
        approved_snapshots = approved_snapshots_for_export(state)
        for snapshot in approved_snapshots:
            snapshot_id = str(snapshot.get("snapshot_id", ""))
            content = _snapshot_content(snapshot)
            teacher_only_paths = teacher_only_value_paths(content)
            if teacher_only_paths:
                raise ExportAdapterError(
                    "Approved snapshot contains teacher-only answer material: "
                    + ", ".join(teacher_only_paths),
                )
            rendered_html = await self.renderer.render(content)
            export_path = export_dir / f"{snapshot_id}.html"
            export_path.write_text(rendered_html, encoding="utf-8")
            exported_files.append(str(export_path))
        for export_format in _subprocess_formats(state):
            out_path = await node_export(export_format, run_id, approved_snapshots, export_dir)
            exported_files.append(out_path)
        return exported_files


@dataclass(frozen=True, slots=True)
class ObjectStorageTeachingPackExportWriter:
    """#118 (OPS-05): the same `write_exports` contract as the filesystem
    writer, but PUTs to S3/MinIO and returns object keys (never local paths).

    Keys are a deterministic function of identity -- `exports/<run_id>/<file>`
    -- never a random per-attempt suffix, so a re-run overwrites the same key
    rather than accumulating duplicates (the property #123/OPS-10 builds on).
    """

    config: ObjectStorageConfig
    client: S3Client
    renderer: TeachingPackSnapshotRenderer = RendererAdapterSnapshotRenderer()

    async def write_exports(self, run_id: RunId, state: JsonObject) -> list[str]:
        unsupported_formats = _unsupported_formats(state)
        if unsupported_formats:
            raise ExportAdapterError(
                "Unsupported export format for offline gateway writer: "
                + ", ".join(unsupported_formats),
            )
        exported_keys: list[str] = []
        approved_snapshots = approved_snapshots_for_export(state)
        for snapshot in approved_snapshots:
            snapshot_id = str(snapshot.get("snapshot_id", ""))
            content = _snapshot_content(snapshot)
            teacher_only_paths = teacher_only_value_paths(content)
            if teacher_only_paths:
                raise ExportAdapterError(
                    "Approved snapshot contains teacher-only answer material: "
                    + ", ".join(teacher_only_paths),
                )
            rendered_html = await self.renderer.render(content)
            key = f"exports/{run_id}/{snapshot_id}.html"
            await self._put_object(key, rendered_html.encode("utf-8"))
            exported_keys.append(key)
        for export_format in _subprocess_formats(state):
            key = await self._node_export_to_object(export_format, run_id, approved_snapshots)
            exported_keys.append(key)
        return exported_keys

    async def _put_object(self, key: str, body: bytes) -> None:
        """Overwrite-safe PUT -- S3 object writes are atomic per-key; the
        same key always fully replaces the previous object, never merges."""
        try:
            await asyncio.to_thread(
                self.client.put_object, Bucket=self.config.bucket, Key=key, Body=body,
            )
        except Exception as exc:  # noqa: BLE001 -- fail-closed, never silently skip the upload
            raise ExportAdapterError(f"Object storage upload failed for key {key!r}: {exc}") from exc

    async def _node_export_to_object(
        self,
        export_format: ExportFormat,
        run_id: RunId,
        snapshots: list[JsonObject],
    ) -> str:
        """The Node CLI only writes to a local directory -- give it a temp
        dir, upload the produced file, then let the context manager clean
        up. Preserves node_export's existing fail-closed timeout/exit-code
        handling verbatim; only the sink after a successful run changes."""
        with tempfile.TemporaryDirectory(prefix="omc-export-") as temp_dir:
            local_path = await node_export(export_format, run_id, snapshots, Path(temp_dir))
            body = Path(local_path).read_bytes()
        key = f"exports/{run_id}/{run_id}.{export_format}"
        await self._put_object(key, body)
        return key

    def presigned_url(self, key: str, *, expires_in_seconds: int = 300) -> str:
        from services.gateway.object_storage import presigned_export_url

        return presigned_export_url(
            self.client, bucket=self.config.bucket, key=key, expires_in_seconds=expires_in_seconds,
        )


def export_writer_for_environment(
    environment: str,
    *,
    base_dir: Path = Path(".scratch/pipeline-v2/artifacts/exports"),
) -> TeachingPackExportWriter:
    """#118: env-mapped writer selection, mirroring the store-factory
    pattern at `main.py:167-172` (`if environment in ("staging", "production")`).
    `development` (and anything else, fail-open to the safest default for
    local dev) keeps the unchanged filesystem writer; only staging/production
    write to object storage."""
    if environment in ("staging", "production"):
        from services.gateway.object_storage import (
            apply_export_lifecycle_rules,
            build_s3_client,
            ensure_bucket_exists,
            object_storage_config_from_env,
        )
        from services.gateway.retention import RetentionConfig

        config = object_storage_config_from_env()
        client = build_s3_client(config)
        ensure_bucket_exists(client, config.bucket)
        # #120 (OPS-07): align object expiry with the DB `artifacts`
        # retention so a signed URL never outlives (or is outlived by) its
        # DB key -- see `object_storage.py`'s `EXPORTS_LIFECYCLE_RULE_ID`
        # docstring for what this rule can and can't prove.
        apply_export_lifecycle_rules(
            client, config.bucket, expiration_days=RetentionConfig().artifacts,
        )
        return ObjectStorageTeachingPackExportWriter(config=config, client=client)
    return FileSystemTeachingPackExportWriter(base_dir=base_dir)


@dataclass(frozen=True, slots=True)
class TeachingPackBundleWriter:
    """Renders every approved artifact in a run as one combined standalone
    HTML document via the renderer's `teaching_pack` plugin (ADR-056), rather
    than one file per artifact. Not gated by the per-(artifact_type, format)
    capability matrix in export_manifest_service.py -- a bundle isn't a single
    artifact export, it's always html, which is unconditionally supported."""

    base_dir: Path = Path(".scratch/pipeline-v2/artifacts/exports")
    renderer: TeachingPackSnapshotRenderer = RendererAdapterSnapshotRenderer()

    async def write_bundle(
        self,
        run_id: RunId,
        approved_snapshots: list[JsonObject],
        *,
        title: str,
        subject: str,
        grade_level: str,
    ) -> str:
        if not approved_snapshots:
            raise ExportAdapterError("No approved artifacts to bundle into a Teaching Pack export")
        children = [
            {"id": str(snapshot.get("artifact_id", "")), "input": _snapshot_content(snapshot)}
            for snapshot in approved_snapshots
        ]
        bundle_content: JsonObject = {
            "artifact_type": "teaching_pack",
            "title": title,
            "subject": subject,
            "gradeLevel": grade_level,
            "children": children,
        }
        rendered_html = await self.renderer.render(bundle_content)
        export_dir = self.base_dir / str(run_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{run_id}.teaching_pack.html"
        export_path.write_text(rendered_html, encoding="utf-8")
        return str(export_path)


def _approved_snapshot_ids(state: JsonObject) -> set[str]:
    values = state.get("approved_snapshot_ids", [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


def approved_snapshots_for_export(state: JsonObject) -> list[JsonObject]:
    """The exact snapshots (with snapshot_id/artifact_id) an export was built from.

    SDE-06: this is the one source of truth for "what snapshot_id did this
    export come from" — callers must pass this through explicitly rather
    than re-deriving/inferring a snapshot_id at read time.
    """
    approved_ids = _approved_snapshot_ids(state)
    return [
        snapshot for snapshot in _rendered_snapshots(state)
        if str(snapshot.get("snapshot_id", "")) in approved_ids
    ]


def _rendered_snapshots(state: JsonObject) -> list[JsonObject]:
    values = state.get("rendered_snapshots")
    if not isinstance(values, list):
        approval_gate = _json_object(state.get("approval_gate"))
        values = approval_gate.get("rendered_snapshots")
    if not isinstance(values, list):
        return []
    return [_json_object(value) for value in values if isinstance(value, dict)]


def _snapshot_content(snapshot: JsonObject) -> JsonObject:
    content = _json_object(snapshot.get("content_json"))
    if "artifact_type" in content:
        return content
    artifact_type = snapshot.get("artifact_type")
    if not isinstance(artifact_type, str) or not artifact_type:
        return content
    return {**content, "artifact_type": artifact_type}


_SUBPROCESS_EXPORT_FORMATS: frozenset[str] = frozenset(
    {"gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "pptx"},
)
_UNSUPPORTED_GATEWAY_FORMATS: frozenset[str] = frozenset({"google_forms"})


def _subprocess_formats(state: JsonObject) -> list[ExportFormat]:
    contract = _json_object(state.get("contract"))
    values = contract.get("export_formats")
    if not isinstance(values, list):
        return []
    return [
        export_format
        for value in values
        if (export_format := _export_format(str(value))) in _SUBPROCESS_EXPORT_FORMATS
    ]


def _unsupported_formats(state: JsonObject) -> list[str]:
    contract = _json_object(state.get("contract"))
    values = contract.get("export_formats")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value) in _UNSUPPORTED_GATEWAY_FORMATS]


def _export_format(value: str) -> ExportFormat:
    match value:
        case "html":
            return "html"
        case "gift":
            return "gift"
        case "h5p":
            return "h5p"
        case "qti":
            return "qti"
        case "anki_apkg":
            return "anki_apkg"
        case "flashcard_tsv":
            return "flashcard_tsv"
        case "pptx":
            return "pptx"
        case _:
            raise ExportAdapterError(f"Unsupported export format: {value}")


async def node_export(
    export_format: ExportFormat,
    run_id: RunId,
    snapshots: list[JsonObject],
    export_dir: Path,
) -> str:
    """Invoke the Node export CLI bridge and return the written file path.

    Fails closed: raises ExportAdapterError on subprocess failure, timeout,
    or missing CLI build. Never silently falls back to HTML. Shared by the
    completion-time writer above and the explicit regeneration path in
    export_manifest_service.py.
    """
    if not _EXPORT_CLI_PATH.exists():
        raise ExportAdapterError(
            f"Export CLI not built — run: pnpm --filter @oh-my-class/exporters build"
            f" (expected: {_EXPORT_CLI_PATH})"
        )

    artifacts = [
        {
            "artifact_type": str(snapshot.get("artifact_type", "")),
            "content": _json_object(snapshot.get("content_json")),
        }
        for snapshot in snapshots
    ]
    payload = json.dumps(
        {
            "format": export_format,
            "run_id": str(run_id),
            "artifacts": artifacts,
            "output_dir": str(export_dir),
        },
        ensure_ascii=False,
    ).encode("utf-8")

    try:
        process = await asyncio.create_subprocess_exec(
            "node", str(_EXPORT_CLI_PATH),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=payload),
                timeout=_EXPORT_CLI_TIMEOUT,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise ExportAdapterError(
                f"Export CLI timed out after {_EXPORT_CLI_TIMEOUT}s for format {export_format}"
            ) from None
    except (OSError, ValueError) as exc:
        raise ExportAdapterError(f"Failed to start export CLI: {exc}") from exc

    exit_code = process.returncode
    stdout_text = stdout_bytes.decode("utf-8") if stdout_bytes else ""
    stderr_text = stderr_bytes.decode("utf-8") if stderr_bytes else ""

    if exit_code != 0:
        raise ExportAdapterError(
            f"Export CLI exited {exit_code} for format {export_format}",
            exit_code=exit_code,
            stderr=stderr_text or None,
        )

    try:
        result = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise ExportAdapterError(
            f"Export CLI returned invalid JSON: {stdout_text!r}"
        ) from exc

    if "error" in result:
        raise ExportAdapterError(f"Export CLI error: {result['error']}")

    return str(result["path"])


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}
