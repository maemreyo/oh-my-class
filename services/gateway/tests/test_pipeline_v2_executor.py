from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_executor import (
    PipelineV2Executor,
    PipelineV2FailureRecorder,
    PipelineV2ResumeJob,
    PipelineV2StartJob,
)
from services.gateway.pipeline_v2_models import PipelineV2EventVisibility
from services.gateway.pipeline_v2_store import PipelineV2EventCreate, PipelineV2StatusTransition
from services.gateway.pipeline_v2_types import JsonObject, RunId

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from langgraph.types import Command

    from packages.agents.pipeline_v2.graph import LangGraphRunnableConfig


@dataclass(slots=True)
class RecordingTaskGroup:
    scheduled: list[str] = field(default_factory=list)

    def start_soon(self, func: Callable[[PipelineV2StartJob], Awaitable[None]], *args) -> None:
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
        self.transitions: list[PipelineV2StatusTransition] = []
        self.events: list[PipelineV2EventCreate] = []

    async def transition_status(self, payload: PipelineV2StatusTransition) -> None:
        self.transitions.append(payload)

    async def write_event(self, payload: PipelineV2EventCreate) -> None:
        self.events.append(payload)


class TestPipelineV2Executor:
    @pytest.mark.anyio
    async def test_enqueue_start_job_schedules_without_invoking_graph(self) -> None:
        graph = RecordingGraph()
        task_group = RecordingTaskGroup()
        executor = PipelineV2Executor(graph, task_group)

        await executor.enqueue_start_job(PipelineV2StartJob(
            run_id=RunId("run-1"),
            initial_state={"run_id": "run-1"},
        ))

        assert task_group.scheduled == ["_run_start_job"]
        assert graph.calls == []

    @pytest.mark.anyio
    async def test_run_start_job_invokes_graph_with_run_thread_id(self) -> None:
        graph = RecordingGraph()
        task_group = RecordingTaskGroup()
        executor = PipelineV2Executor(graph, task_group)

        await executor._run_start_job(PipelineV2StartJob(
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
        executor = PipelineV2Executor(graph, task_group)

        await executor.enqueue_resume_job(PipelineV2ResumeJob(
            run_id=RunId("run-1"),
            gate_response_id="response-1",
            resume_payload={"action": "approve"},
        ))

        assert task_group.scheduled == ["_run_resume_job"]
        assert graph.calls == []

    @pytest.mark.anyio
    async def test_run_start_job_persists_failure_before_reraising(self) -> None:
        failure_sink = RecordingFailureSink()
        executor = PipelineV2Executor(FailingGraph(), RecordingTaskGroup(), failure_sink)

        with pytest.raises(RuntimeError, match="graph failed"):
            await executor._run_start_job(PipelineV2StartJob(
                run_id=RunId("run-1"),
                initial_state={"run_id": "run-1"},
            ))

        assert failure_sink.failures == [(RunId("run-1"), "RuntimeError: graph failed")]

    @pytest.mark.anyio
    async def test_failure_recorder_persists_status_and_event(self) -> None:
        store = RecordingFailureStore()
        recorder = PipelineV2FailureRecorder(store)

        await recorder.persist_failure(RunId("run-1"), "RuntimeError: graph failed")

        assert store.transitions == [PipelineV2StatusTransition(
            run_id=RunId("run-1"),
            status=RunStatus.FAILED,
            stage=None,
            reason="RuntimeError: graph failed",
        )]
        assert store.events == [PipelineV2EventCreate(
            run_id=RunId("run-1"),
            event_name="pipeline_v2.run.failed",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"error": "RuntimeError: graph failed"},
        )]
