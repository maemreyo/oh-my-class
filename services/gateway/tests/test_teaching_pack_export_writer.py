from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from services.gateway.teaching_pack_export_writer import ExportAdapterError, FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_types import JsonObject, RunId


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body>oh-my-class export</body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


class TestTeachingPackExportWriter:
    @pytest.mark.anyio
    async def test_filesystem_writer_fails_fast_for_unknown_export_format(
        self,
        tmp_path: Path,
    ) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=RecordingRenderer())
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html", "unknown_format"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }

        with pytest.raises(ExportAdapterError, match="unknown_format"):
            await writer.write_exports(RunId("run-unknown-export"), state)
