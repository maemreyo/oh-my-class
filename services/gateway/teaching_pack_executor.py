from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from langgraph.errors import EmptyInputError
from langgraph.types import Command

from packages.agents.llm.error_summary import safe_error_summary
from packages.agents.teaching_pack.graph import LangGraphRunnableConfig, teaching_pack_thread_config
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import (
    TeachingPackEventCreate,
    TeachingPackStatusTransition,
)
from services.gateway.teaching_pack_types import JsonObject, RunId

from .teaching_pack_executor_types import TeachingPackNotificationSink, TeachingPackRunEventStore

_log = logging.getLogger(__name__)


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


class TeachingPackFailureRecorder:
    def __init__(
        self,
        store: TeachingPackRunEventStore,
        notifications: TeachingPackNotificationSink | None = None,
    ) -> None:
        self._store = store
        self._notifications = notifications

    async def persist_failure(self, run_id: RunId, error_summary: str) -> None:
        run = await self._store.get_run_by_id(run_id)
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
        if self._notifications is not None and run is not None:
            await self._notifications.notify_failed(run_id, run.teacher_id, error_summary)

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
        except EmptyInputError:
            # The LangGraph checkpoint for this thread is missing — the in-memory
            # checkpointer (MemorySaver) was cleared by a process restart. The run
            # cannot be resumed without its checkpoint. Mark it failed so the teacher
            # can restart from scratch rather than leaving it stuck in AWAITING_APPROVAL.
            _log.error(
                "resume.no_checkpoint run_id=%s — checkpoint lost (process restart?); run marked FAILED",
                job.run_id,
            )
            await self._persist_failure(job.run_id, EmptyInputError(
                "LangGraph checkpoint lost (process restart). Re-start the run to regenerate."
            ))
            raise
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
