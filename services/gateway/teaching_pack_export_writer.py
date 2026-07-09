from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from services.gateway.teaching_pack_types import JsonObject, RunId

type ExportFormat = Literal["html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "google_forms"]

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
        approved_ids = _approved_snapshot_ids(state)
        export_dir = self.base_dir / str(run_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        unsupported_formats = _unsupported_formats(state)
        if unsupported_formats:
            raise ExportAdapterError(
                "Unsupported export format for offline gateway writer: "
                + ", ".join(unsupported_formats),
            )
        exported_files: list[str] = []
        approved_snapshots: list[JsonObject] = []
        for snapshot in _rendered_snapshots(state):
            snapshot_id = str(snapshot.get("snapshot_id", ""))
            if snapshot_id not in approved_ids:
                continue
            approved_snapshots.append(snapshot)
            rendered_html = await self.renderer.render(_snapshot_content(snapshot))
            export_path = export_dir / f"{snapshot_id}.html"
            export_path.write_text(rendered_html, encoding="utf-8")
            exported_files.append(str(export_path))
        for export_format in _subprocess_formats(state):
            out_path = await _node_export(export_format, run_id, approved_snapshots, export_dir)
            exported_files.append(out_path)
        return exported_files


def _approved_snapshot_ids(state: JsonObject) -> set[str]:
    values = state.get("approved_snapshot_ids", [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


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


_SUBPROCESS_EXPORT_FORMATS: frozenset[str] = frozenset({"gift", "h5p", "qti", "anki_apkg", "flashcard_tsv"})
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
        case _:
            raise ExportAdapterError(f"Unsupported export format: {value}")


async def _node_export(
    export_format: ExportFormat,
    run_id: RunId,
    snapshots: list[JsonObject],
    export_dir: Path,
) -> str:
    """Invoke the Node export CLI bridge and return the written file path.

    Fails closed: raises ExportAdapterError on subprocess failure, timeout,
    or missing CLI build. Never silently falls back to HTML.
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
