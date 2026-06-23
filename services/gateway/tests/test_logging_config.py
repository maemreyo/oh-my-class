"""Tests for logging_config module."""

import logging
import sys
from pathlib import Path

# Required: pytest's path setup omits workspace member paths that uv run injects.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from services.gateway.logging_config import (  # noqa: E402
    DEFAULT_LOG_LEVEL,
    JSON_FORMAT,
    bind_context,
    configure_logging,
    get_logger,
)


class TestConfigureLogging:
    """Tests for configure_logging()."""

    def test_configure_logging_no_crash(self) -> None:
        """configure_logging runs without error for both modes."""
        configure_logging(log_level="INFO", json_output=True)
        configure_logging(log_level="DEBUG", json_output=False)

    def test_configure_logging_sets_level(self) -> None:
        """After configure, root logger respects the given level."""
        configure_logging(log_level="WARNING", json_output=True)
        root_level = logging.getLogger().level
        assert root_level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger()."""

    def test_get_logger_returns_logger(self) -> None:
        """get_logger returns an object with standard logging methods."""
        logger = get_logger("test.module")
        assert hasattr(logger, "info")
        assert callable(logger.info)
        assert hasattr(logger, "debug")
        assert callable(logger.debug)
        assert hasattr(logger, "error")
        assert callable(logger.error)

    def test_get_logger_default_name(self) -> None:
        """get_logger with no args returns a logger with default name."""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_actually_logs(self) -> None:
        """get_logger returns a logger that can emit messages without raising."""
        configure_logging(log_level="DEBUG", json_output=True)
        logger = get_logger("test.emit")
        logger.info("test message")


class TestBindContext:
    """Tests for bind_context()."""

    def test_bind_context_no_crash(self) -> None:
        """bind_context doesn't raise with any combination of kwargs."""
        configure_logging(log_level="INFO", json_output=True)
        logger = get_logger("test.bind")

        # No context
        result = bind_context(logger)
        assert result is not None

        # Full context
        result = bind_context(
            logger,
            request_id="req-1",
            teacher_id="t-001",
            run_id="run-123",
            step=5,
            agent="planner",
        )
        assert result is not None

        # Partial context
        result = bind_context(logger, run_id="run-456", agent="reviewer")
        assert result is not None

    def test_bind_context_partial_fields(self) -> None:
        """bind_context only binds provided (non-None) fields."""
        configure_logging(log_level="INFO", json_output=False)
        logger = get_logger("test.partial")
        result = bind_context(logger, request_id="r-1", agent="content_creator")
        assert result is not None

    def test_constants_defined(self) -> None:
        """Module constants are defined and have expected types."""
        assert isinstance(DEFAULT_LOG_LEVEL, str)
        assert isinstance(JSON_FORMAT, bool)
