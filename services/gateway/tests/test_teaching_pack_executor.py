from __future__ import annotations

from dataclasses import dataclass, field
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
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackStatusTransition
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

    async def transition_status(self, payload: TeachingPackStatusTransition) -> None:
        self.transitions.append(payload)

    async def write_event(self, payload: TeachingPackEventCreate) -> None:
        self.events.append(payload)


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
