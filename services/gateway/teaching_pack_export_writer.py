from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from services.gateway.teaching_pack_types import JsonObject, RunId


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
        exported_files: list[str] = []
        for snapshot in _rendered_snapshots(state):
            snapshot_id = str(snapshot.get("snapshot_id", ""))
            if snapshot_id not in approved_ids:
                continue
            rendered_html = await self.renderer.render(_json_object(snapshot.get("content_json")))
            export_path = export_dir / f"{snapshot_id}.html"
            export_path.write_text(rendered_html, encoding="utf-8")
            exported_files.append(str(export_path))
        return exported_files


def _approved_snapshot_ids(state: JsonObject) -> set[str]:
    values = state.get("approved_snapshot_ids", [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


def _rendered_snapshots(state: JsonObject) -> list[JsonObject]:
    values = state.get("rendered_snapshots")
    if not isinstance(values, list):
        return []
    return [_json_object(value) for value in values if isinstance(value, dict)]


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}
