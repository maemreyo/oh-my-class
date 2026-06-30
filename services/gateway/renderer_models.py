"""Shared renderer adapter models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from services.gateway.exceptions import ErrorCode, OMCError

DEFAULT_COMMAND: tuple[str, ...] = (
    "node",
    "packages/renderer/dist/agent-renderer.js",
)
DEFAULT_TIMEOUT_SECONDS: float = 30.0
DEFAULT_RENDERER_VERSION = "0.1.0"
DEFAULT_TEMPLATE_VERSION = "0.1.0"
type RendererBackend = Literal["pool", "subprocess"]


@dataclass(frozen=True, slots=True)
class RendererConfig:
    command: tuple[str, ...] = DEFAULT_COMMAND
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    backend: RendererBackend = "pool"
    pool_size: int = 2
    max_concurrent_renders: int = 4
    max_retries: int = 1
    renderer_version: str = DEFAULT_RENDERER_VERSION
    template_version: str = DEFAULT_TEMPLATE_VERSION


class RendererAdapterError(OMCError):
    """Raised when the renderer backend fails or produces invalid output."""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.PIPELINE_ERROR,
            message=message,
        )
        self.exit_code = exit_code
        self.stderr = stderr
