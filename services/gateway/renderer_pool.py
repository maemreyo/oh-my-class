"""Long-lived renderer worker pool."""
from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from services.gateway.renderer_models import RendererAdapterError, RendererConfig


class WorkerRequest(TypedDict):
    renderer_version: str
    template_version: str
    artifact: dict[str, Any]


class RenderVersionContext(TypedDict):
    rendererVersion: str


class RenderContext(TypedDict):
    audience: str
    locale: str
    theme: str
    renderMode: str
    requestId: str
    versions: RenderVersionContext
    assetPolicy: str


class WorkerRenderRequest(TypedDict):
    requestId: str
    kind: str
    input: Any
    context: RenderContext


class WorkerResponse(TypedDict, total=False):
    ok: bool
    html: str
    manifest: NotRequired[dict[str, Any]]
    diagnostics: NotRequired[list[dict[str, Any]]]
    metrics: NotRequired[dict[str, Any]]
    error: str | WorkerError
    stderr: str


class WorkerError(TypedDict, total=False):
    code: str
    category: str
    retryable: bool
    message: str
    details: dict[str, Any]


@dataclass(slots=True)
class RendererWorker:  # noqa: MUTABLE_OK
    process: asyncio.subprocess.Process
    lock: asyncio.Lock


class RendererPool:
    def __init__(self, config: RendererConfig) -> None:
        self._config = config
        self._workers: list[RendererWorker] = []
        self._next_worker = 0
        self._pool_lock = asyncio.Lock()
        self._capacity = asyncio.Semaphore(config.max_concurrent_renders)

    async def render(self, artifact_content: dict[str, Any]) -> str:
        request: WorkerRequest = {
            "renderer_version": self._config.renderer_version,
            "template_version": self._config.template_version,
            "artifact": artifact_content,
        }
        return await self._render_request(request)

    async def render_v2(self, request: WorkerRenderRequest) -> str:
        return await self._render_request(request)

    async def _render_request(self, request: WorkerRequest | WorkerRenderRequest) -> str:
        async with self._capacity:
            last_error: RendererAdapterError | None = None
            for _ in range(self._config.max_retries + 1):
                worker = await self._borrow_worker()
                try:
                    return await self._render_with_worker(worker, request)
                except RendererAdapterError as exc:
                    last_error = exc
                    if not exc.retryable:
                        raise
                    await self._replace_worker(worker)
            if last_error is not None:
                raise last_error
            raise RendererAdapterError("Renderer pool failed without an error")

    async def _borrow_worker(self) -> RendererWorker:
        async with self._pool_lock:
            while len(self._workers) < self._config.pool_size:
                self._workers.append(await start_worker(self._config))
            worker = self._workers[self._next_worker % len(self._workers)]
            self._next_worker += 1
            return worker

    async def _replace_worker(self, worker: RendererWorker) -> None:
        async with self._pool_lock:
            if worker in self._workers:
                self._workers.remove(worker)
            await terminate_worker(worker)

    async def _render_with_worker(
        self,
        worker: RendererWorker,
        request: WorkerRequest | WorkerRenderRequest,
    ) -> str:
        async with worker.lock:
            if worker.process.stdin is None or worker.process.stdout is None:
                raise RendererAdapterError("Renderer worker missing stdio pipes")
            try:
                worker.process.stdin.write(
                    json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n",
                )
                await worker.process.stdin.drain()
                response_line = await asyncio.wait_for(
                    worker.process.stdout.readline(),
                    timeout=self._config.timeout_seconds,
                )
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise RendererAdapterError("Renderer worker pipe failed") from exc
            except RuntimeError as exc:
                # asyncio raises RuntimeError when transport.write() is called on a
                # closed transport — the subprocess exited and its stdin pipe was
                # garbage-collected or explicitly closed. Treat the same as a broken pipe.
                raise RendererAdapterError("Renderer worker transport closed") from exc
            except TimeoutError:
                raise RendererAdapterError(
                    f"Renderer worker timed out after {self._config.timeout_seconds}s",
                ) from None
        if not response_line:
            stderr = await read_stderr(worker.process)
            raise RendererAdapterError("Renderer worker exited before responding", stderr=stderr)
        return parse_worker_response(response_line, worker.process.returncode)


async def start_worker(config: RendererConfig) -> RendererWorker:
    try:
        process = await asyncio.create_subprocess_exec(
            *config.command,
            "--worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (OSError, ValueError) as exc:
        raise RendererAdapterError(f"Failed to start renderer worker: {exc}") from exc
    return RendererWorker(process=process, lock=asyncio.Lock())


async def terminate_worker(worker: RendererWorker) -> None:
    if worker.process.returncode is None:
        worker.process.kill()
        await worker.process.wait()


async def read_stderr(process: asyncio.subprocess.Process) -> str | None:
    if process.stderr is None:
        return None
    with contextlib.suppress(TimeoutError):
        stderr = await asyncio.wait_for(process.stderr.read(), timeout=0.1)
        return stderr.decode("utf-8") if stderr else None
    return None


def parse_worker_response(response_line: bytes, exit_code: int | None) -> str:
    from services.gateway.renderer_adapter import validate_rendered_html

    try:
        response: WorkerResponse = json.loads(response_line.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RendererAdapterError("Renderer worker produced invalid JSON") from exc
    if not response.get("ok", False):
        error = response.get("error", "Renderer worker failed")
        match error:
            case {"message": message}:
                raise RendererAdapterError(
                    str(message),
                    exit_code=exit_code,
                    retryable=bool(error.get("retryable", False)),
                    renderer_code=str(error.get("code")) if error.get("code") is not None else None,
                    renderer_category=str(error.get("category")) if error.get("category") is not None else None,
                )
            case str(message):
                raise RendererAdapterError(
                    message,
                    exit_code=exit_code,
                    stderr=response.get("stderr"),
                )
            case unreachable:
                raise RendererAdapterError(
                    f"Renderer worker failed with malformed error payload: {unreachable}",
                    exit_code=exit_code,
                )
    return validate_rendered_html(response.get("html", ""), exit_code)


PoolKey = tuple[RendererConfig, int]


_POOLS: dict[PoolKey, RendererPool] = {}


def _pool_key(config: RendererConfig) -> PoolKey:
    return (config, id(asyncio.get_running_loop()))


def pool_for(config: RendererConfig) -> RendererPool:
    key = _pool_key(config)
    pool = _POOLS.get(key)
    if pool is None:
        pool = RendererPool(config)
        _POOLS[key] = pool
    return pool


async def close_renderer_pools() -> None:
    pools = list(_POOLS.values())
    _POOLS.clear()
    for pool in pools:
        for worker in list(pool._workers):
            await terminate_worker(worker)
