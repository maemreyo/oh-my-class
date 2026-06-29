from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from services.gateway.models import RunStatus
from services.gateway.teaching_pack_executor import (
    TeachingPackCompletionRecorder,
    TeachingPackExecutor,
    TeachingPackFailureRecorder,
    TeachingPackResumeJob,
    TeachingPackStartJob,
)
from services.gateway.teaching_pack_export_writer import FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackGateCreate,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langgraph.types import Command

    from packages.agents.teaching_pack.graph import LangGraphRunnableConfig


@dataclass(slots=True)
class RecordingTaskGroup:
    scheduled: list[str] = field(default_factory=list)

    def start_soon(self, func: Callable[[TeachingPackStartJob], Awaitable[None]], *args) -> None:
        self.scheduled.append(func.__name__)


class RecordingGraph:
    def __init__(self) -> None:
        self.calls: list[tuple[JsonObject | Command[tuple[()]], LangGraphRunnableConfig]] = []

    async def ainvoke(
        self,
        input_data: JsonObject | Command[tuple[()]],
        *,
        config: LangGraphRunnableConfig,
    ) -> JsonObject:
        self.calls.append((input_data, config))
        return {"ok": True}


class FailingGraph:
    async def ainvoke(
        self,
        input_data: JsonObject | Command[tuple[()]],
        *,
        config: LangGraphRunnableConfig,
    ) -> JsonObject:
        _ = (input_data, config)
        raise RuntimeError("graph failed")


class RecordingFailureSink:
    def __init__(self) -> None:
        self.failures: list[tuple[RunId, str]] = []

    async def persist_failure(self, run_id: RunId, error_summary: str) -> None:
        self.failures.append((run_id, error_summary))


class RecordingFailureStore:
    def __init__(self) -> None:
        self.transitions: list[TeachingPackStatusTransition] = []
        self.events: list[TeachingPackEventCreate] = []
        self.snapshots: list[ArtifactSnapshotCreate] = []
        self.gates: list[TeachingPackGateCreate] = []

    async def transition_status(self, payload: TeachingPackStatusTransition) -> None:
        self.transitions.append(payload)

    async def write_event(self, payload: TeachingPackEventCreate) -> None:
        self.events.append(payload)

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


@dataclass(slots=True)
class RecordingExportWriter:
    exported_files: list[str] = field(default_factory=lambda: ["exports/run-1/snapshot-1.html"])
    calls: list[tuple[RunId, JsonObject]] = field(default_factory=list)

    async def write_exports(self, run_id: RunId, state: JsonObject) -> list[str]:
        self.calls.append((run_id, state))
        return self.exported_files


class TestTeachingPackExecutor:
    @pytest.mark.anyio
    async def test_enqueue_start_job_schedules_without_invoking_graph(self) -> None:
        graph = RecordingGraph()
        task_group = RecordingTaskGroup()
        executor = TeachingPackExecutor(graph, task_group)

        await executor.enqueue_start_job(TeachingPackStartJob(
            run_id=RunId("run-1"),
            initial_state={"run_id": "run-1"},
        ))

        assert task_group.scheduled == ["_run_start_job"]
        assert graph.calls == []

    @pytest.mark.anyio
    async def test_run_start_job_invokes_graph_with_run_thread_id(self) -> None:
        graph = RecordingGraph()
        task_group = RecordingTaskGroup()
        executor = TeachingPackExecutor(graph, task_group)

        await executor._run_start_job(TeachingPackStartJob(
            run_id=RunId("run-1"),
            initial_state={"run_id": "run-1"},
        ))

        assert graph.calls == [(
            {"run_id": "run-1"},
            {"configurable": {"thread_id": "run-1"}},
        )]

    @pytest.mark.anyio
    async def test_enqueue_resume_job_schedules_without_invoking_graph(self) -> None:
        graph = RecordingGraph()
        task_group = RecordingTaskGroup()
        executor = TeachingPackExecutor(graph, task_group)

        await executor.enqueue_resume_job(TeachingPackResumeJob(
            run_id=RunId("run-1"),
            gate_response_id="response-1",
            resume_payload={"action": "approve"},
        ))

        assert task_group.scheduled == ["_run_resume_job"]
        assert graph.calls == []

    @pytest.mark.anyio
    async def test_run_start_job_persists_failure_before_reraising(self) -> None:
        failure_sink = RecordingFailureSink()
        executor = TeachingPackExecutor(FailingGraph(), RecordingTaskGroup(), failure_sink)

        with pytest.raises(RuntimeError, match="graph failed"):
            await executor._run_start_job(TeachingPackStartJob(
                run_id=RunId("run-1"),
                initial_state={"run_id": "run-1"},
            ))

        assert failure_sink.failures == [(RunId("run-1"), "RuntimeError: graph failed")]

    @pytest.mark.anyio
    async def test_failure_recorder_persists_status_and_event(self) -> None:
        store = RecordingFailureStore()
        recorder = TeachingPackFailureRecorder(store)

        await recorder.persist_failure(RunId("run-1"), "RuntimeError: graph failed")

        assert store.transitions == [TeachingPackStatusTransition(
            run_id=RunId("run-1"),
            status=RunStatus.FAILED,
            stage=None,
            reason="RuntimeError: graph failed",
        )]
        assert store.events == [TeachingPackEventCreate(
            run_id=RunId("run-1"),
            event_name="teaching_pack.run.failed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"error": "RuntimeError: graph failed"},
        )]

    @pytest.mark.anyio
    async def test_completion_recorder_fails_closed_without_export_evidence(self) -> None:
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
    async def test_completion_recorder_renders_snapshots_before_opening_content_gate(self) -> None:
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
                        "rendered_html": "<!DOCTYPE html><html><body>graph html</body></html>",
                    }],
                },
            }],
        })

        assert renderer.calls == [artifact]
        assert store.snapshots[0].rendered_html == renderer.rendered_html
        assert store.snapshots[0].student_rendered_html is None
        assert store.gates[0].gate_name == "content_approval"

    @pytest.mark.anyio
    async def test_completion_recorder_writes_real_exports_before_completed_event(self) -> None:
        store = RecordingFailureStore()
        export_writer = RecordingExportWriter()
        recorder = TeachingPackCompletionRecorder(
            store,
            RecordingRenderer(),
            export_writer,
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

    @pytest.mark.anyio
    async def test_filesystem_export_writer_materializes_approved_snapshot_html(self, tmp_path: Path) -> None:
        renderer = RecordingRenderer(
            rendered_html="<!DOCTYPE html><html><body>oh-my-class export</body></html>",
        )
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "rendered_snapshots": [
                {
                    "snapshot_id": "snapshot-1",
                    "content_json": {"title": "Approved"},
                },
                {
                    "snapshot_id": "snapshot-2",
                    "content_json": {"title": "Unapproved"},
                },
            ],
        }

        exported_files = await writer.write_exports(RunId("run-exports"), state)

        assert exported_files == [str(tmp_path / "run-exports" / "snapshot-1.html")]
        assert (tmp_path / "run-exports" / "snapshot-1.html").read_text(encoding="utf-8") == renderer.rendered_html
        assert not (tmp_path / "run-exports" / "snapshot-2.html").exists()
