from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from services.gateway.models import RunStatus
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_export_writer import FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackGateCreate,
    TeachingPackRunRead,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId


class RecordingFailureStore:
    def __init__(self) -> None:
        self.transitions: list[TeachingPackStatusTransition] = []
        self.events: list[TeachingPackEventCreate] = []
        self.snapshots: list[ArtifactSnapshotCreate] = []
        self.gates: list[TeachingPackGateCreate] = []

    async def get_run_by_id(self, run_id: RunId) -> TeachingPackRunRead | None:
        return TeachingPackRunRead(
            run_id=run_id,
            teacher_id=TeacherId("teacher-1"),
            status=RunStatus.PENDING,
            raw_request="Test run",
        )

    async def transition_status(self, payload: TeachingPackStatusTransition) -> None:
        self.transitions.append(payload)

    async def write_event(self, payload: TeachingPackEventCreate) -> object:
        self.events.append(payload)
        return payload

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> str:
        self.snapshots.append(payload)
        return "content-hash"

    async def open_gate(self, payload: TeachingPackGateCreate) -> None:
        self.gates.append(payload)


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body><main>renderer html</main></body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


@pytest.mark.anyio
async def test_content_gate_renders_snapshot_with_snapshot_artifact_type_when_content_omits_it() -> None:
    store = RecordingFailureStore()
    renderer = RecordingRenderer()
    recorder = TeachingPackCompletionRecorder(store, renderer)

    await recorder.persist_completion(RunId("run-1"), {
        "__interrupt__": [{
            "value": {
                "gate": "content_approval",
                "snapshot_ids": ["snapshot-1"],
                "rendered_snapshots": [{
                    "snapshot_id": "snapshot-1",
                    "artifact_id": "slides-1",
                    "artifact_type": "slide_deck",
                    "content_json": {"title": "Food Vocabulary"},
                }],
            },
        }],
    })

    assert renderer.calls == [{"title": "Food Vocabulary", "artifact_type": "slide_deck"}]
    assert store.snapshots[0].content_json == {
        "title": "Food Vocabulary",
        "artifact_type": "slide_deck",
    }


@pytest.mark.anyio
async def test_filesystem_export_writer_renders_snapshot_with_snapshot_artifact_type(
    tmp_path: Path,
) -> None:
    renderer = RecordingRenderer(
        rendered_html="<!DOCTYPE html><html><body>oh-my-class slide deck export</body></html>",
    )
    writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
    state = {
        "approved_snapshot_ids": ["snapshot-1"],
        "rendered_snapshots": [{
            "snapshot_id": "snapshot-1",
            "artifact_type": "slide_deck",
            "content_json": {"title": "Food Vocabulary"},
        }],
    }

    exported_files = await writer.write_exports(RunId("run-exports"), state)

    assert exported_files == [str(tmp_path / "run-exports" / "snapshot-1.html")]
    assert renderer.calls == [{"title": "Food Vocabulary", "artifact_type": "slide_deck"}]


@pytest.mark.anyio
async def test_filesystem_export_writer_uses_approval_gate_snapshots_when_top_level_is_missing(
    tmp_path: Path,
) -> None:
    renderer = RecordingRenderer(
        rendered_html="<!DOCTYPE html><html><body>oh-my-class slide deck export</body></html>",
    )
    writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
    state = {
        "approved_snapshot_ids": ["snapshot-1"],
        "approval_gate": {
            "rendered_snapshots": [{
                "snapshot_id": "snapshot-1",
                "artifact_type": "slide_deck",
                "content_json": {"title": "Food Vocabulary"},
            }],
        },
    }

    exported_files = await writer.write_exports(RunId("run-exports"), state)

    assert exported_files == [str(tmp_path / "run-exports" / "snapshot-1.html")]
    assert (tmp_path / "run-exports" / "snapshot-1.html").exists()
    assert renderer.calls == [{"title": "Food Vocabulary", "artifact_type": "slide_deck"}]
