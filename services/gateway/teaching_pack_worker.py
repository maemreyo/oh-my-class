from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, assert_never

import anyio

from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_models import RunJobKind

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobRead
    from services.gateway.teaching_pack_types import JsonObject


@dataclass(frozen=True, slots=True)
class TeachingPackWorkerConfig:
    worker_id: str
    lease_seconds: int
    idle_sleep_seconds: float = 1.0
    promote_batch_size: int = 5
    worker_concurrency: int = 1
    heartbeat_interval_seconds: float | None = None


class TeachingPackJobExecutor(Protocol):
    async def run_start_job(self, job: TeachingPackStartJob) -> None: ...

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None: ...


class TeachingPackWorker:
    def __init__(
        self,
        job_store: TeachingPackJobStore,
        executor: TeachingPackJobExecutor,
        config: TeachingPackWorkerConfig,
        heartbeat_session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._job_store = job_store
        self._executor = executor
        self._config = config
        self._heartbeat_session_factory = heartbeat_session_factory

    async def run_one(self, now: datetime | None = None) -> bool:
        job = await self._job_store.claim_next(
            lease_owner=self._config.worker_id,
            lease_seconds=self._config.lease_seconds,
            now=now,
        )
        if job is None:
            return False
        try:
            await self._execute_with_heartbeat(job)
        except Exception as exc:
            await self._handle_job_error(job, exc, now=now)
        else:
            await self._job_store.mark_completed(job.job_id)
        await _persist_observability_events(self._job_store, str(job.run_id))
        await self._job_store.promote_eligible(
            limit=self._config.promote_batch_size,
            now=now,
        )
        return True

    async def run_claimed(self, job: RunJobRead) -> None:
        try:
            await self._execute_with_heartbeat(job)
        except Exception as exc:
            await self._handle_job_error(job, exc)
        else:
            await self._job_store.mark_completed(job.job_id)
        await _persist_observability_events(self._job_store, str(job.run_id))

    async def _handle_job_error(
        self,
        job: RunJobRead,
        exc: Exception,
        now: datetime | None = None,
    ) -> None:
        from packages.llm_client.errors import TransientProviderError

        # anyio wraps exceptions from task groups in ExceptionGroup; unwrap
        # a single-exception group so our isinstance checks work correctly.
        root = exc
        if isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
            root = exc.exceptions[0]

        if isinstance(root, TransientProviderError):
            from datetime import UTC, datetime as _datetime, timedelta
            now = now or _datetime.now(UTC)
            eligible_at = now + timedelta(seconds=root.retry_after_seconds)
            await self._job_store.requeue_with_backoff(job.job_id, eligible_at)
        else:
            await self._job_store.mark_failed(job.job_id)

    async def run_loop(self, max_iterations: int | None = None) -> int:
        completed = 0
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            iterations += 1
            did_work = await self.run_one()
            if did_work:
                completed += 1
                continue
            if max_iterations is not None:
                return completed
            await anyio.sleep(self._config.idle_sleep_seconds)
        return completed

    async def _execute(self, job: RunJobRead) -> None:
        match job.kind:
            case RunJobKind.START:
                await self._executor.run_start_job(TeachingPackStartJob(
                    run_id=job.run_id,
                    initial_state=_initial_state(job),
                ))
            case RunJobKind.RESUME:
                await self._executor.run_resume_job(TeachingPackResumeJob(
                    run_id=job.run_id,
                    gate_response_id=str(job.payload.get("response_id", "")),
                    resume_payload=_resume_payload(job),
                ))
            case unreachable:
                assert_never(unreachable)

    async def _execute_with_heartbeat(self, job: RunJobRead) -> None:
        interval = self._heartbeat_interval()
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(self._heartbeat, job.job_id, interval)
            try:
                await self._execute(job)
            finally:
                task_group.cancel_scope.cancel()

    async def _heartbeat(self, job_id: str, interval: float) -> None:
        while True:
            await anyio.sleep(interval)
            if self._heartbeat_session_factory is not None:
                async with self._heartbeat_session_factory() as session:
                    from services.gateway.teaching_pack_job_store import TeachingPackJobStore

                    refreshed = await TeachingPackJobStore(session).refresh_lease(
                        job_id=job_id,
                        lease_owner=self._config.worker_id,
                        lease_seconds=self._config.lease_seconds,
                    )
                    await session.commit()
                if not refreshed:
                    return
                continue
            refreshed = await self._job_store.refresh_lease(
                job_id=job_id,
                lease_owner=self._config.worker_id,
                lease_seconds=self._config.lease_seconds,
            )
            if not refreshed:
                return

    def _heartbeat_interval(self) -> float:
        if self._config.heartbeat_interval_seconds is not None:
            return self._config.heartbeat_interval_seconds
        return max(self._config.lease_seconds / 3, 1.0)


async def run_worker_batch(
    session_factory: async_sessionmaker[AsyncSession],
    executor_factory: Callable[[AsyncSession], TeachingPackJobExecutor],
    config: TeachingPackWorkerConfig,
) -> int:
    claimed = 0
    async with anyio.create_task_group() as task_group:
        for _ in range(config.worker_concurrency):
            async with session_factory() as session:
                from services.gateway.teaching_pack_job_store import TeachingPackJobStore

                store = TeachingPackJobStore(session)
                job = await store.claim_next(config.worker_id, config.lease_seconds)
                await session.commit()
            if job is None:
                continue
            claimed += 1
            task_group.start_soon(_run_claimed_job, session_factory, executor_factory, config, job)
    return claimed


async def _run_claimed_job(
    session_factory: async_sessionmaker[AsyncSession],
    executor_factory: Callable[[AsyncSession], TeachingPackJobExecutor],
    config: TeachingPackWorkerConfig,
    job: RunJobRead,
) -> None:
    async with session_factory() as session:
        from services.gateway.teaching_pack_job_store import TeachingPackJobStore

        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor_factory(session),
            config,
            heartbeat_session_factory=session_factory,
        )
        await worker.run_claimed(job)
        await session.commit()


def _initial_state(job: RunJobRead) -> JsonObject:
    initial_state = job.payload.get("initial_state")
    if isinstance(initial_state, dict):
        return initial_state
    contract = job.payload.get("contract")
    if isinstance(contract, dict):
        return {"run_id": job.run_id, "contract": contract}
    return {"run_id": job.run_id}


def _resume_payload(job: RunJobRead) -> JsonObject:
    resume_payload = job.payload.get("resume_payload")
    if isinstance(resume_payload, dict):
        return resume_payload
    return {"response_id": job.payload.get("response_id", "")}


async def _persist_observability_events(
    store: TeachingPackJobStore,
    run_id: str,
) -> None:
    from packages.agents.events import drain_observability_events
    from services.gateway.teaching_pack_models import TeachingPackEventVisibility
    from services.gateway.teaching_pack_store import TeachingPackRunStore

    run_store = TeachingPackRunStore(store.session)
    for event in drain_observability_events(run_id):
        visibility = TeachingPackEventVisibility.TEACHER if event.event_type in {
            "stage_transition",
            "gate_decision",
            "healing_decision",
            "escalate",
            "breaker_tripped",
        } else TeachingPackEventVisibility.INTERNAL
        await run_store.write_observability_event(event, visibility=visibility)
