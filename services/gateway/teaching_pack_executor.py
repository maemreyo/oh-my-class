from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from langgraph.types import Command

from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.teaching_pack.graph import LangGraphRunnableConfig, teaching_pack_thread_config
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_export_writer import (
    FileSystemTeachingPackExportWriter,
    RendererAdapterSnapshotRenderer,
    TeachingPackExportWriter,
    TeachingPackSnapshotRenderer,
)
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_store import ArtifactSnapshotCreate
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackGateCreate,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId


@dataclass(frozen=True, slots=True)
class TeachingPackStartJob:
    run_id: RunId
    initial_state: JsonObject


@dataclass(frozen=True, slots=True)
class TeachingPackResumeJob:
    run_id: RunId
    gate_response_id: str
    resume_payload: JsonObject


class TeachingPackGraph(Protocol):
    async def ainvoke(
        self,
        input_data: JsonObject | Command[tuple[()]],
        *,
        config: LangGraphRunnableConfig,
    ) -> JsonObject: ...


class TeachingPackTaskGroup(Protocol):
    def start_soon(self, func, *args) -> None: ...


class TeachingPackFailureStore(Protocol):
    async def transition_status(self, payload: TeachingPackStatusTransition) -> None: ...

    async def write_event(self, payload: TeachingPackEventCreate): ...

    async def create_snapshot(self, payload: ArtifactSnapshotCreate) -> str: ...

    async def open_gate(self, payload: TeachingPackGateCreate) -> None: ...


class TeachingPackFailureRecorder:
    def __init__(self, store: TeachingPackFailureStore) -> None:
        self._store = store

    async def persist_failure(self, run_id: RunId, error_summary: str) -> None:
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.FAILED,
            stage=None,
            reason=error_summary,
        ))
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.run.failed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"error": error_summary},
        ))


class TeachingPackCompletionRecorder:
    def __init__(
        self,
        store: TeachingPackFailureStore,
        renderer: TeachingPackSnapshotRenderer | None = None,
        export_writer: TeachingPackExportWriter | None = None,
    ) -> None:
        self._store = store
        self._renderer = renderer or RendererAdapterSnapshotRenderer()
        self._export_writer = export_writer or FileSystemTeachingPackExportWriter(
            renderer=self._renderer,
        )

    async def persist_completion(self, run_id: RunId, state: JsonObject) -> None:
        gate_payload = _content_gate_payload(state)
        if gate_payload is not None:
            await self._persist_content_gate(run_id, gate_payload)
            return
        if _has_export_evidence(state):
            exported_files = await self._export_writer.write_exports(run_id, state)
            await self._store.transition_status(TeachingPackStatusTransition(
                run_id=run_id,
                status=RunStatus.EXPORTING,
                stage="export_finalize",
                reason="export_started",
            ))
            await self._store.transition_status(TeachingPackStatusTransition(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                stage=None,
                reason="completed",
            ))
            await self._store.write_event(TeachingPackEventCreate(
                run_id=run_id,
                event_name="teaching_pack.run.completed",
                visibility=TeachingPackEventVisibility.TEACHER,
                payload={"exported_files": exported_files},
            ))
            return
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.FAILED,
            stage=None,
            reason="missing_export_evidence",
        ))
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.run.failed",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"error": "V2 graph completed without export evidence"},
        ))

    async def _persist_content_gate(self, run_id: RunId, gate_payload: JsonObject) -> None:
        for snapshot in _rendered_snapshots(gate_payload):
            content_json = _json_object(snapshot.get("content_json"))
            rendered_html = await self._renderer.render(content_json)
            await self._store.create_snapshot(ArtifactSnapshotCreate(
                snapshot_id=str(snapshot["snapshot_id"]),
                run_id=run_id,
                artifact_id=str(snapshot["artifact_id"]),
                artifact_type=str(snapshot["artifact_type"]),
                content_json=content_json,
                rendered_html=rendered_html,
                student_rendered_html=None,
                renderer_version=str(snapshot.get("renderer_version", "renderer-adapter")),
                template_version=str(snapshot.get("template_version", "eta-agent-renderer")),
                theme_version=str(snapshot.get("theme_version", "default")),
            ))
        gate_id = f"gate-{uuid4()}"
        await self._store.open_gate(TeachingPackGateCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={"gate_id": gate_id, **gate_payload},
        ))
        await self._store.transition_status(TeachingPackStatusTransition(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            stage="content_approval",
            reason="content_approval",
        ))
        await self._store.write_event(TeachingPackEventCreate(
            run_id=run_id,
            event_name="teaching_pack.content_approval.opened",
            visibility=TeachingPackEventVisibility.TEACHER,
            payload={"gate_id": gate_id, "snapshot_ids": gate_payload.get("snapshot_ids", [])},
        ))


class TeachingPackFailureSink(Protocol):
    async def persist_failure(self, run_id: RunId, error_summary: str) -> None: ...


class TeachingPackCompletionSink(Protocol):
    async def persist_completion(self, run_id: RunId, state: JsonObject) -> None: ...


class TeachingPackExecutor:
    def __init__(
        self,
        graph: TeachingPackGraph,
        task_group: TeachingPackTaskGroup,
        failure_sink: TeachingPackFailureSink | None = None,
        completion_sink: TeachingPackCompletionSink | None = None,
    ) -> None:
        self._graph = graph
        self._task_group = task_group
        self._failure_sink = failure_sink
        self._completion_sink = completion_sink

    async def enqueue_start(self, run_id: str) -> None:
        self._task_group.start_soon(self._noop_start, RunId(run_id))

    async def enqueue_resume(self, run_id: str, gate_response_id: str) -> None:
        self._task_group.start_soon(
            self._noop_resume,
            TeachingPackResumeJob(
                run_id=RunId(run_id),
                gate_response_id=gate_response_id,
                resume_payload={},
            ),
        )

    async def enqueue_start_job(self, job: TeachingPackStartJob) -> None:
        self._task_group.start_soon(self._run_start_job, job)

    async def enqueue_resume_job(self, job: TeachingPackResumeJob) -> None:
        self._task_group.start_soon(self._run_resume_job, job)

    async def run_start_job(self, job: TeachingPackStartJob) -> None:
        await self._run_start_job(job)

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None:
        await self._run_resume_job(job)

    async def _run_start_job(self, job: TeachingPackStartJob) -> None:
        try:
            state = await self._graph.ainvoke(
                job.initial_state,
                config=teaching_pack_thread_config(job.run_id),
            )
            await self._persist_completion(job.run_id, state)
        except Exception as exc:
            await self._persist_failure(job.run_id, exc)
            raise

    async def _run_resume_job(self, job: TeachingPackResumeJob) -> None:
        try:
            state = await self._graph.ainvoke(
                Command(resume=job.resume_payload),
                config=teaching_pack_thread_config(job.run_id),
            )
            await self._persist_completion(job.run_id, state)
        except Exception as exc:
            await self._persist_failure(job.run_id, exc)
            raise

    async def _persist_failure(self, run_id: RunId, error: Exception) -> None:
        if self._failure_sink is None:
            return
        await self._failure_sink.persist_failure(run_id, _error_summary(error))

    async def _persist_completion(self, run_id: RunId, state: JsonObject) -> None:
        if self._completion_sink is None:
            return
        await self._completion_sink.persist_completion(run_id, state)

    async def _noop_start(self, run_id: RunId) -> None:
        _ = run_id

    async def _noop_resume(self, job: TeachingPackResumeJob) -> None:
        _ = job


def _error_summary(error: Exception) -> str:
    return safe_error_summary(error)


def _has_export_evidence(state: JsonObject) -> bool:
    exported_files = state.get("exported_files")
    return isinstance(exported_files, list) and len(exported_files) > 0


def _content_gate_payload(state: JsonObject) -> JsonObject | None:
    interrupt_values = state.get("__interrupt__")
    if isinstance(interrupt_values, list) and interrupt_values:
        value = _interrupt_value(interrupt_values[0])
        if value.get("gate") == "content_approval":
            return value
    return None


def _interrupt_value(interrupt_data) -> JsonObject:
    if isinstance(interrupt_data, dict):
        value = interrupt_data.get("value", interrupt_data)
        return _json_object(value)
    value = getattr(interrupt_data, "value", {})
    return _json_object(value)


def _rendered_snapshots(gate_payload: JsonObject) -> list[JsonObject]:
    values = gate_payload.get("rendered_snapshots")
    if not isinstance(values, list):
        return []
    return [_json_object(value) for value in values if isinstance(value, dict)]


def _json_object(value) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}
