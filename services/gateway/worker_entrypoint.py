"""Standalone teaching-pack worker process (#119 OPS-06 -- partial slice).

Runs the same claim/execute loop as the in-process worker embedded in the
gateway's FastAPI lifespan (`main.py::_run_teaching_pack_worker`), but without
starting the FastAPI app -- for `WORKER_MODE != "in_process"` deployments
where the worker fleet scales independently from the API. Builds the
identical graph/checkpointer/store via
`teaching_pack_runtime.build_teaching_pack_runtime` (the same builder
`main.py`'s lifespan uses), so the API and the worker never drift onto two
different code paths.

**What #119 still needs that this module does not provide** (real,
acknowledged gaps -- not attempted here):
- The container image / K8s Deployment (or compose service) manifest.
- Queue-depth autoscaling (KEDA/HPA) driven off pending `run_jobs` count.
- The provider-rate-limit autoscale ceiling.
- The 5,000-packs/day load test proving p95 < 8 min under autoscaling.

Those need a real cluster and a load-test harness this environment can't
stand up or verify. This module is the "standalone worker entrypoint" scope
item only: a process that can run the worker loop independent of the API,
with a distinct `lease_owner` per replica and a breakable claim loop for
graceful drain (the hook #119 says OPS-08 needs).
"""

from __future__ import annotations

import os
import signal
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

import anyio

if TYPE_CHECKING:
    from anyio.abc import TaskGroup

    from services.gateway.teaching_pack_runtime import TeachingPackRuntime
    from services.gateway.teaching_pack_worker import TeachingPackJobExecutor


DEFAULT_LEASE_SECONDS = 120
DEFAULT_IDLE_SLEEP_SECONDS = 1.0
MAX_WORKER_CONCURRENCY = 10


def worker_id() -> str:
    """Distinct per replica -- `claim_next`/`refresh_lease` key leases on
    this, so two replicas sharing an id would corrupt heartbeat semantics
    (per #119's own implementation notes). Pod name / hostname first, a
    pid-based fallback for bare-process/dev use."""
    return os.getenv("POD_NAME") or os.getenv("HOSTNAME") or f"worker-{os.getpid()}"


def _worker_concurrency() -> int:
    raw = os.getenv("WORKER_CONCURRENCY", "1")
    try:
        concurrency = int(raw)
    except ValueError:
        concurrency = 1
    return min(max(concurrency, 1), MAX_WORKER_CONCURRENCY)


def _default_executor_factory(runtime: TeachingPackRuntime, task_group: TaskGroup):
    from services.gateway.artifact_document_content_store import GatewayArtifactDocumentContentStore
    from services.gateway.outcome_delivery import SqlAlchemyOutcomeDeliverySink
    from services.gateway.teaching_pack_completion import TeachingPackCompletionRecorder
    from services.gateway.teaching_pack_executor import TeachingPackExecutor, TeachingPackFailureRecorder
    from services.gateway.teaching_pack_executor_types import InAppTeachingPackNotificationSink
    from services.gateway.teaching_pack_export_store import TeachingPackExportStore
    from services.gateway.teaching_pack_store import TeachingPackRunStore

    class _AnyioTeachingPackTaskGroup:
        def __init__(self, group: TaskGroup) -> None:
            self._group = group

        def start_soon(self, func, *args) -> None:
            self._group.start_soon(func, *args)

    def executor_factory(session):
        run_store = TeachingPackRunStore(session)
        notification_sink = InAppTeachingPackNotificationSink(session)
        return TeachingPackExecutor(
            runtime.graph,
            _AnyioTeachingPackTaskGroup(task_group),
            TeachingPackFailureRecorder(run_store, notification_sink),
            TeachingPackCompletionRecorder(
                run_store,
                export_writer=runtime.export_writer,
                notifications=notification_sink,
                outcome_delivery=SqlAlchemyOutcomeDeliverySink(runtime.session_factory),
                export_store=TeachingPackExportStore(session),
                content_store=GatewayArtifactDocumentContentStore(runtime.session_factory),
            ),
        )

    return executor_factory


async def run_standalone_worker(
    runtime: TeachingPackRuntime,
    *,
    shutdown_event: anyio.Event | None = None,
    executor_factory_override=None,
) -> None:
    """The worker claim/execute loop, independent of any FastAPI app.

    `shutdown_event`, when given, makes the claim loop breakable for
    graceful drain: checked before each batch, and used to interrupt the
    idle sleep immediately rather than waiting out the last `idle_sleep_seconds`
    tick. Runs forever if omitted (the real entrypoint's default).

    `executor_factory_override` exists purely for tests -- letting a test
    drive a real claimed job through a fake executor without running the
    full LLM pipeline, without adding a second production code path.
    """
    from services.gateway.teaching_pack_worker import TeachingPackWorkerConfig, run_worker_batch

    config = TeachingPackWorkerConfig(
        worker_id=worker_id(),
        lease_seconds=DEFAULT_LEASE_SECONDS,
        idle_sleep_seconds=DEFAULT_IDLE_SLEEP_SECONDS,
        worker_concurrency=_worker_concurrency(),
    )

    async with anyio.create_task_group() as task_group:
        executor_factory: TeachingPackJobExecutor = (
            executor_factory_override
            if executor_factory_override is not None
            else _default_executor_factory(runtime, task_group)
        )

        while shutdown_event is None or not shutdown_event.is_set():
            claimed = await run_worker_batch(runtime.session_factory, executor_factory, config)
            if claimed == 0:
                if shutdown_event is not None:
                    with anyio.move_on_after(config.idle_sleep_seconds):
                        await shutdown_event.wait()
                else:
                    await anyio.sleep(config.idle_sleep_seconds)

        task_group.cancel_scope.cancel()


async def main() -> None:
    """Process entrypoint: `python -m services.gateway.worker_entrypoint`.

    Builds its own runtime (own engine, own checkpointer connection --
    entirely separate from any API process) and runs until SIGTERM, then
    drains: stops claiming new jobs, lets in-flight ones finish, and exits.
    """
    from services.gateway.logging_config import configure_logging
    from services.gateway.secrets_guard import validate_production_secrets
    from services.gateway.teaching_pack_runtime import build_teaching_pack_runtime

    configure_logging(log_level="INFO", json_output=True)
    validate_production_secrets()

    environment = os.getenv("OMC_ENVIRONMENT", "development")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
    )

    shutdown_event = anyio.Event()

    def _handle_shutdown_signal() -> None:
        shutdown_event.set()

    async with AsyncExitStack() as stack:
        runtime = await build_teaching_pack_runtime(
            environment=environment, database_url=database_url, exit_stack=stack,
        )
        try:
            with anyio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signals:
                async with anyio.create_task_group() as signal_task_group:

                    async def _wait_for_signal() -> None:
                        async for _ in signals:
                            _handle_shutdown_signal()
                            return

                    signal_task_group.start_soon(_wait_for_signal)
                    await run_standalone_worker(runtime, shutdown_event=shutdown_event)
                    signal_task_group.cancel_scope.cancel()
        finally:
            await runtime.engine.dispose()


if __name__ == "__main__":
    anyio.run(main)
