from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langgraph.types import Command

from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.pipeline_v2.graph import LangGraphRunnableConfig, pipeline_v2_thread_config
from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_models import PipelineV2EventVisibility
from services.gateway.pipeline_v2_store import (
    PipelineV2EventCreate,
    PipelineV2StatusTransition,
)
from services.gateway.pipeline_v2_types import JsonObject, RunId


@dataclass(frozen=True, slots=True)
class PipelineV2StartJob:
    run_id: RunId
    initial_state: JsonObject


@dataclass(frozen=True, slots=True)
class PipelineV2ResumeJob:
    run_id: RunId
    gate_response_id: str
    resume_payload: JsonObject


class PipelineV2Graph(Protocol):
    async def ainvoke(
        self,
        input_data: JsonObject | Command[tuple[()]],
        *,
        config: LangGraphRunnableConfig,
    ) -> JsonObject: ...


class PipelineV2TaskGroup(Protocol):
    def start_soon(self, func, *args) -> None: ...


class PipelineV2FailureStore(Protocol):
    async def transition_status(self, payload: PipelineV2StatusTransition) -> None: ...

    async def write_event(self, payload: PipelineV2EventCreate): ...


class PipelineV2FailureRecorder:
    def __init__(self, store: PipelineV2FailureStore) -> None:
        self._store = store

    async def persist_failure(self, run_id: RunId, error_summary: str) -> None:
        await self._store.transition_status(PipelineV2StatusTransition(
            run_id=run_id,
            status=RunStatus.FAILED,
            stage=None,
            reason=error_summary,
        ))
        await self._store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.run.failed",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"error": error_summary},
        ))


class PipelineV2FailureSink(Protocol):
    async def persist_failure(self, run_id: RunId, error_summary: str) -> None: ...


class PipelineV2Executor:
    def __init__(
        self,
        graph: PipelineV2Graph,
        task_group: PipelineV2TaskGroup,
        failure_sink: PipelineV2FailureSink | None = None,
    ) -> None:
        self._graph = graph
        self._task_group = task_group
        self._failure_sink = failure_sink

    async def enqueue_start(self, run_id: str) -> None:
        self._task_group.start_soon(self._noop_start, RunId(run_id))

    async def enqueue_resume(self, run_id: str, gate_response_id: str) -> None:
        self._task_group.start_soon(
            self._noop_resume,
            PipelineV2ResumeJob(
                run_id=RunId(run_id),
                gate_response_id=gate_response_id,
                resume_payload={},
            ),
        )

    async def enqueue_start_job(self, job: PipelineV2StartJob) -> None:
        self._task_group.start_soon(self._run_start_job, job)

    async def enqueue_resume_job(self, job: PipelineV2ResumeJob) -> None:
        self._task_group.start_soon(self._run_resume_job, job)

    async def run_start_job(self, job: PipelineV2StartJob) -> None:
        await self._run_start_job(job)

    async def run_resume_job(self, job: PipelineV2ResumeJob) -> None:
        await self._run_resume_job(job)

    async def _run_start_job(self, job: PipelineV2StartJob) -> None:
        try:
            await self._graph.ainvoke(
                job.initial_state,
                config=pipeline_v2_thread_config(job.run_id),
            )
        except Exception as exc:
            await self._persist_failure(job.run_id, exc)
            raise

    async def _run_resume_job(self, job: PipelineV2ResumeJob) -> None:
        try:
            await self._graph.ainvoke(
                Command(resume=job.resume_payload),
                config=pipeline_v2_thread_config(job.run_id),
            )
        except Exception as exc:
            await self._persist_failure(job.run_id, exc)
            raise

    async def _persist_failure(self, run_id: RunId, error: Exception) -> None:
        if self._failure_sink is None:
            return
        await self._failure_sink.persist_failure(run_id, _error_summary(error))

    async def _noop_start(self, run_id: RunId) -> None:
        _ = run_id

    async def _noop_resume(self, job: PipelineV2ResumeJob) -> None:
        _ = job


def _error_summary(error: Exception) -> str:
    return safe_error_summary(error)
