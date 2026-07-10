from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
from services.gateway.teaching_pack_export_store import ExportRecordCreate
from services.gateway.teaching_pack_export_writer import ExportAdapterError, FileSystemTeachingPackExportWriter
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


@dataclass(slots=True)
class RecordingExportStore:
    records: list[ExportRecordCreate] = field(default_factory=list)

    async def create_export_record(self, payload: ExportRecordCreate) -> ExportRecordCreate:
        self.records.append(payload)
        return payload


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
        assert store.events[0].payload.get("content_artifacts") == []

    @pytest.mark.anyio
    async def test_hydrates_reference_snapshot_before_opening_content_gate(self) -> None:
        store = RecordingFailureStore()
        renderer = RecordingRenderer()
        content_store = InMemoryArtifactContentStore()
        artifact = ArtifactContent(
            artifact_id="artifact-1",
            artifact_type="lesson",
            theme="default",
            title="Durable Lesson",
            sections=[{"title": "Intro", "content": "A durable projection."}],
            metadata={},
            accessibility={"language": "en"},
        )
        reference = await content_store.persist("run-1", "run-1:artifact:1", artifact, "artifact-1")
        recorder = TeachingPackCompletionRecorder(store, renderer, content_store=content_store)

        await recorder.persist_completion(RunId("run-1"), {
            "__interrupt__": [{
                "value": {
                    "gate": "content_approval",
                    "snapshot_ids": ["snapshot-1"],
                    "rendered_snapshots": [{
                        "snapshot_id": "snapshot-1",
                        "artifact_id": "artifact-1",
                        "artifact_type": "lesson",
                        "document_id": reference.document_id,
                    }],
                },
            }],
        })

        assert renderer.calls == [artifact.model_dump(mode="json")]
        assert store.snapshots[0].content_json == artifact.model_dump(mode="json")

    @pytest.mark.anyio
    async def test_hydrates_reference_snapshot_before_export(self) -> None:
        store = RecordingFailureStore()
        content_store = InMemoryArtifactContentStore()
        artifact = ArtifactContent(
            artifact_id="artifact-1",
            artifact_type="lesson",
            theme="default",
            title="Durable Lesson",
            sections=[{"title": "Intro", "content": "A durable projection."}],
            metadata={},
            accessibility={"language": "en"},
        )
        reference = await content_store.persist("run-1", "run-1:artifact:1", artifact, "artifact-1")
        export_writer = RecordingExportWriter()
        recorder = TeachingPackCompletionRecorder(
            store,
            export_writer=export_writer,
            content_store=content_store,
        )

        await recorder.persist_completion(RunId("run-1"), {
            "run_id": "run-1",
            "exported_files": ["exports/run-1/snapshot-1.html"],
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [{
                "snapshot_id": "snapshot-1",
                "artifact_id": "artifact-1",
                "artifact_type": "lesson",
                "document_id": reference.document_id,
            }],
        })

        export_state = export_writer.calls[0][1]
        assert export_state["rendered_snapshots"][0]["content_json"] == artifact.model_dump(mode="json")

    @pytest.mark.anyio
    async def test_content_update_event_is_teacher_visible_before_next_gate(self) -> None:
        store = RecordingFailureStore()
        renderer = RecordingRenderer()
        recorder = TeachingPackCompletionRecorder(store, renderer)
        artifact = {
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "title": "Rendered Lesson",
            "sections": [],
        }

        await recorder.persist_completion(RunId("run-1"), {
            "content_update_event": {
                "event_name": "teaching_pack.content_version.created",
                "payload": {"artifact_id": "lesson-1", "authority": "teacher_edit"},
            },
            "__interrupt__": [{
                "value": {
                    "gate": "content_approval",
                    "snapshot_ids": ["snapshot-1"],
                    "content_artifacts": [artifact],
                    "rendered_snapshots": [{
                        "snapshot_id": "snapshot-1",
                        "artifact_id": "lesson-1",
                        "artifact_type": "lesson",
                        "content_json": artifact,
                    }],
                },
            }],
        })

        assert store.events[0] == TeachingPackEventCreate(
            run_id=RunId("run-1"),
            event_name="teaching_pack.content_version.created",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"artifact_id": "lesson-1", "authority": "teacher_edit"},
        )
        assert store.events[1].event_name == "teaching_pack.content_approval.opened"
        assert store.events[1].payload["content_artifacts"] == [artifact]

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
    async def test_export_finalize_persists_export_record_with_source_snapshot_id(self) -> None:
        """SDE-06: the export record's snapshot_id is the snapshot actually
        exported (passed through explicitly), not "whatever is current"."""
        store = RecordingFailureStore()
        export_writer = RecordingExportWriter(
            exported_files=["exports/run-1/snapshot-1.html"],
        )
        export_store = RecordingExportStore()
        recorder = TeachingPackCompletionRecorder(
            store,
            RecordingRenderer(),
            export_writer,
            export_store=export_store,
        )
        state = {
            "run_id": "run-1",
            "exported_files": ["exports/run-1/snapshot-1.html"],
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [{
                "snapshot_id": "snapshot-1",
                "artifact_id": "artifact-1",
                "content_json": {"title": "Lesson"},
            }],
        }

        await recorder.persist_completion(RunId("run-1"), state)

        assert len(export_store.records) == 1
        record = export_store.records[0]
        assert record.snapshot_id == "snapshot-1"
        assert record.artifact_id == "artifact-1"
        assert record.format == "html"
        assert record.storage_path == "exports/run-1/snapshot-1.html"

    @pytest.mark.anyio
    async def test_export_finalize_without_export_evidence_never_creates_export_record(self) -> None:
        """SDE-06: no automatic re-export/export-record creation is ever
        triggered by anything other than a successful export — an edit alone
        (no export evidence in state) must not create a record."""
        store = RecordingFailureStore()
        export_store = RecordingExportStore()
        recorder = TeachingPackCompletionRecorder(store, export_store=export_store)

        await recorder.persist_completion(RunId("run-1"), {"run_id": "run-1"})

        assert export_store.records == []

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
        from unittest.mock import patch

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

        async def fake_node_export(
            fmt: str,
            run_id: str,
            _: list[JsonObject],
            export_dir: Path,
        ) -> str:
            path = export_dir / f"{run_id}.{fmt.replace('gift', 'gift.txt').replace('h5p', 'h5p').replace('qti', 'qti.xml')}"
            path.write_text(f"fake {fmt}", encoding="utf-8")
            return str(path)

        with patch(
            "services.gateway.teaching_pack_export_writer._node_export",
            side_effect=fake_node_export,
        ):
            exported_files = await writer.write_exports(RunId("run-assessment"), state)

        assert str(tmp_path / "run-assessment" / "snapshot-1.html") in exported_files
        assert any("gift" in f for f in exported_files)
        assert any("h5p" in f for f in exported_files)
        assert any("qti" in f for f in exported_files)

    @pytest.mark.anyio
    async def test_filesystem_export_writer_fails_fast_for_google_forms(
        self,
        tmp_path: Path,
    ) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=RecordingRenderer())
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html", "google_forms"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }

        with pytest.raises(ExportAdapterError, match="google_forms"):
            await writer.write_exports(RunId("run-google-forms"), state)
