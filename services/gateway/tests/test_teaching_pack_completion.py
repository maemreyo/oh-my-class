from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from services.gateway.models import RunStatus
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_export_writer import FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
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


class RecordingNotificationSink:
    def __init__(self) -> None:
        self.completed: list[tuple[RunId, str]] = []
        self.failed: list[tuple[RunId, str, str]] = []

    async def notify_completed(self, run_id: RunId, teacher_id: str) -> None:
        self.completed.append((run_id, teacher_id))

    async def notify_failed(self, run_id: RunId, teacher_id: str, error_summary: str) -> None:
        self.failed.append((run_id, teacher_id, error_summary))


@dataclass(slots=True)
class RecordingOutcomeDeliverySink:
    calls: list[tuple[RunId, str, JsonObject]] = field(default_factory=list)

    async def record_post_export_delivery(
        self,
        run_id: RunId,
        teacher_id: str,
        state: JsonObject,
    ) -> None:
        self.calls.append((run_id, teacher_id, state))


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body><main>renderer html</main></body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


@dataclass(slots=True)
class RecordingExportWriter:
    exported_files: list[str] = field(default_factory=lambda: ["exports/run-1/snapshot-1.html"])
    calls: list[tuple[RunId, JsonObject]] = field(default_factory=list)

    async def write_exports(self, run_id: RunId, state: JsonObject) -> list[str]:
        self.calls.append((run_id, state))
        return self.exported_files


class TestTeachingPackCompletionRecorder:
    @pytest.mark.anyio
    async def test_fails_closed_without_export_evidence(self) -> None:
        store = RecordingFailureStore()
        recorder = TeachingPackCompletionRecorder(store)

        await recorder.persist_completion(RunId("run-1"), {"run_id": "run-1"})

        assert store.transitions == [TeachingPackStatusTransition(
            run_id=RunId("run-1"),
            status=RunStatus.FAILED,
            stage=None,
            reason="missing_export_evidence",
        )]
        assert store.events == [TeachingPackEventCreate(
            run_id=RunId("run-1"),
            event_name="teaching_pack.run.failed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"error": "V2 graph completed without export evidence"},
        )]

    @pytest.mark.anyio
    async def test_renders_snapshots_before_opening_content_gate(self) -> None:
        store = RecordingFailureStore()
        renderer = RecordingRenderer()
        recorder = TeachingPackCompletionRecorder(store, renderer)
        artifact = {
            "artifact_id": "artifact-1",
            "artifact_type": "lesson",
            "title": "Rendered Lesson",
            "sections": [],
        }

        await recorder.persist_completion(RunId("run-1"), {
            "__interrupt__": [{
                "value": {
                    "gate": "content_approval",
                    "snapshot_ids": ["snapshot-1"],
                    "rendered_snapshots": [{
                        "snapshot_id": "snapshot-1",
                        "artifact_id": "artifact-1",
                        "artifact_type": "lesson",
                        "content_json": artifact,
                    }],
                },
            }],
        })

        assert renderer.calls == [artifact]
        assert store.snapshots[0].rendered_html == renderer.rendered_html
        assert store.snapshots[0].student_rendered_html is None
        assert store.gates[0].gate_name == "content_approval"

    @pytest.mark.anyio
    async def test_writes_real_exports_and_notifies_teacher_before_completed_event(self) -> None:
        store = RecordingFailureStore()
        export_writer = RecordingExportWriter()
        notifications = RecordingNotificationSink()
        outcome_delivery = RecordingOutcomeDeliverySink()
        recorder = TeachingPackCompletionRecorder(
            store,
            RecordingRenderer(),
            export_writer,
            notifications,
            outcome_delivery,
        )
        state = {
            "run_id": "run-1",
            "exported_files": ["exports/run-1/snapshot-1.html"],
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [{
                "snapshot_id": "snapshot-1",
                "content_json": {"title": "Lesson"},
            }],
        }

        await recorder.persist_completion(RunId("run-1"), state)

        assert export_writer.calls == [(RunId("run-1"), state)]
        assert store.events[-1].payload == {"exported_files": ["exports/run-1/snapshot-1.html"]}
        assert notifications.completed == [(RunId("run-1"), "teacher-1")]
        assert outcome_delivery.calls == [(RunId("run-1"), "teacher-1", state)]

    @pytest.mark.anyio
    async def test_auto_approval_is_teacher_visible_before_completion(self) -> None:
        store = RecordingFailureStore()
        export_writer = RecordingExportWriter()
        recorder = TeachingPackCompletionRecorder(store, RecordingRenderer(), export_writer)
        state = {
            "run_id": "run-1",
            "exported_files": ["exports/run-1/snapshot-1.html"],
            "approved_snapshot_ids": ["snapshot-1"],
            "approval_gate": {
                "gate_name": "content_approval",
                "auto_approved": True,
                "snapshot_ids": ["snapshot-1"],
            },
        }

        await recorder.persist_completion(RunId("run-1"), state)

        assert store.events[-2] == TeachingPackEventCreate(
            run_id=RunId("run-1"),
            event_name="teaching_pack.content_approval.auto_approved",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"gate_name": "content_approval", "snapshot_ids": ["snapshot-1"]},
        )
        assert store.events[-1].event_name == "teaching_pack.run.completed"

    @pytest.mark.anyio
    async def test_persists_render_quality_recovery_route(self) -> None:
        store = RecordingFailureStore()
        recorder = TeachingPackCompletionRecorder(store)

        await recorder.persist_completion(RunId("run-1"), {
            "run_id": "run-1",
            "quality_recovery_route": "post_blueprint_research",
            "quality_issues": ["pack.coherence:factual_uncertainty"],
            "quality_scores": {"passed": False, "overall": 0.0},
        })

        assert store.transitions == [TeachingPackStatusTransition(
            run_id=RunId("run-1"),
            status=RunStatus.PLANNING,
            stage="post_blueprint_research",
            reason="quality_recovery:post_blueprint_research",
        )]
        assert store.events == [TeachingPackEventCreate(
            run_id=RunId("run-1"),
            event_name="teaching_pack.quality_recovery.started",
            visibility=TeachingPackEventVisibility.INTERNAL,
            payload={
                "route": "post_blueprint_research",
                "issues": ["pack.coherence:factual_uncertainty"],
            },
        )]

    @pytest.mark.anyio
    async def test_filesystem_export_writer_materializes_approved_snapshot_html(
        self,
        tmp_path: Path,
    ) -> None:
        renderer = RecordingRenderer(
            rendered_html="<!DOCTYPE html><html><body>oh-my-class export</body></html>",
        )
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [
                {"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}},
                {"snapshot_id": "snapshot-2", "content_json": {"title": "Unapproved"}},
            ],
        }

        exported_files = await writer.write_exports(RunId("run-exports"), state)

        assert exported_files == [str(tmp_path / "run-exports" / "snapshot-1.html")]
        assert (tmp_path / "run-exports" / "snapshot-1.html").read_text(
            encoding="utf-8",
        ) == renderer.rendered_html
        assert not (tmp_path / "run-exports" / "snapshot-2.html").exists()

    @pytest.mark.anyio
    async def test_filesystem_export_writer_materializes_assessment_formats(
        self,
        tmp_path: Path,
    ) -> None:
        renderer = RecordingRenderer(
            rendered_html="<!DOCTYPE html><html><body>oh-my-class export</body></html>",
        )
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html", "gift", "h5p", "qti"]},
            "rendered_snapshots": [
                {
                    "snapshot_id": "snapshot-1",
                    "content_json": {
                        "artifact_id": "lesson-1",
                        "artifact_type": "lesson",
                        "title": "Equivalent Fractions",
                        "sections": [{"title": "Intro", "content": "Compare equal fractions."}],
                    },
                }
            ],
        }

        exported_files = await writer.write_exports(RunId("run-assessment"), state)

        assert exported_files == [
            str(tmp_path / "run-assessment" / "snapshot-1.html"),
            str(tmp_path / "run-assessment" / "run-assessment.gift.txt"),
            str(tmp_path / "run-assessment" / "run-assessment.h5p"),
            str(tmp_path / "run-assessment" / "run-assessment.qti.xml"),
        ]
        assert (tmp_path / "run-assessment" / "run-assessment.gift.txt").read_text(
            encoding="utf-8",
        ).startswith("$CATEGORY: oh-my-class/run-assessment")
        assert (tmp_path / "run-assessment" / "run-assessment.h5p").read_bytes().startswith(
            b'{"schema":"oh-my-class.h5p.manifest.v1"',
        )
        assert "imsqti_v2p1" in (tmp_path / "run-assessment" / "run-assessment.qti.xml").read_text(
            encoding="utf-8",
        )
