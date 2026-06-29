from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, assert_never

import anyio

from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_models import RunJobKind

if TYPE_CHECKING:
    from datetime import datetime

    from services.gateway.teaching_pack_job_store import TeachingPackJobStore, RunJobRead
    from services.gateway.teaching_pack_types import JsonObject


@dataclass(frozen=True, slots=True)
class TeachingPackWorkerConfig:
    worker_id: str
    lease_seconds: int
    idle_sleep_seconds: float = 1.0
    promote_batch_size: int = 5


class TeachingPackJobExecutor(Protocol):
    async def run_start_job(self, job: TeachingPackStartJob) -> None: ...

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None: ...


class TeachingPackWorker:
    def __init__(
        self,
        job_store: TeachingPackJobStore,
        executor: TeachingPackJobExecutor,
        config: TeachingPackWorkerConfig,
    ) -> None:
        self._job_store = job_store
        self._executor = executor
        self._config = config

    async def run_one(self, now: datetime | None = None) -> bool:
        job = await self._job_store.claim_next(
            lease_owner=self._config.worker_id,
            lease_seconds=self._config.lease_seconds,
            now=now,
        )
        if job is None:
            return False
        try:
            await self._execute(job)
        except Exception:
            await self._job_store.mark_failed(job.job_id)
        else:
            await self._job_store.mark_completed(job.job_id)
        await self._job_store.promote_eligible(
            limit=self._config.promote_batch_size,
            now=now,
        )
        return True

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
