"""Structured logging configuration for oh-my-class gateway.

Provides structlog with stdlib fallback when structlog is not installed.

Usage::

    from logging_config import configure_logging, get_logger, bind_context

    configure_logging(log_level="INFO", json_output=True)
    logger = get_logger("my.module")
    logger = bind_context(logger, request_id="abc", teacher_id="t-001")
    logger.info("pipeline.started", run_id="run-123", step=3)
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# ── Constants ────────────────────────────────────────────────

DEFAULT_LOG_LEVEL: str = "INFO"
JSON_FORMAT: bool = True

# ── Structlog availability check ─────────────────────────────

try:
    import structlog  # type: ignore[reportUnusedImport]

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None  # type: ignore[assignment]
    _STRUCTLOG_AVAILABLE = False


# ── Stdlib JSON formatter (fallback) ─────────────────────────


class _JsonFormatter(logging.Formatter):
    """JSON log formatter for stdlib fallback."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


# ── Public API ───────────────────────────────────────────────


def configure_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    json_output: bool = JSON_FORMAT,
) -> None:
    """Configure structured logging for the gateway.

    If structlog is available, configures structlog with processors.
    Otherwise, falls back to stdlib logging with JSON formatting.
    """
    if _STRUCTLOG_AVAILABLE:
        _configure_structlog(log_level, json_output)
    else:
        _configure_stdlib(log_level, json_output)


def get_logger(name: str = "omc") -> Any:
    """Return a bound logger for the given name.

    Returns a structlog BoundLogger if available, else a stdlib Logger.
    """
    if _STRUCTLOG_AVAILABLE:
        import structlog  # Re-import for type checker
        return structlog.get_logger(name)
    return logging.getLogger(name)


def bind_context(
    logger: Any,
    *,
    request_id: str | None = None,
    teacher_id: str | None = None,
    run_id: str | None = None,
    step: int | str | None = None,
    agent: str | None = None,
) -> Any:
    """Bind pipeline context to a logger and return the bound logger.

    Skips any None values — only binds fields that are provided.
    """
    context: dict[str, Any] = {}
    if request_id is not None:
        context["request_id"] = request_id
    if teacher_id is not None:
        context["teacher_id"] = teacher_id
    if run_id is not None:
        context["run_id"] = run_id
    if step is not None:
        context["step"] = step
    if agent is not None:
        context["agent"] = agent

    if not context:
        return logger

    if _STRUCTLOG_AVAILABLE:
        return logger.bind(**context)

    # Stdlib: attach context as extra — accessible via record.__dict__
    for key, value in context.items():
        setattr(logger, key, value)
    return logger


# ── Private helpers ──────────────────────────────────────────


def _configure_structlog(log_level: str, json_output: bool) -> None:
    """Configure structlog processors and renderer."""
    if not _STRUCTLOG_AVAILABLE:
        return
    
    import structlog  # Re-import for type checker
    
    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also set root logger level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
        stream=sys.stderr,
    )


def _configure_stdlib(log_level: str, json_output: bool) -> None:
    """Configure stdlib logging with optional JSON formatting."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicate output
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)

    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root.addHandler(handler)
