"""Tests for log_context."""

from common.contracts.log_context import LogContext


class TestLogContext:
    """Test suite for LogContext."""

    def test_log_context_defaults(self):
        """All fields default to empty string or None."""
        ctx = LogContext()
        assert ctx.request_id == ""
        assert ctx.teacher_id == ""
        assert ctx.run_id == ""
        assert ctx.step is None
        assert ctx.agent is None
        assert ctx.timestamp == ""

    def test_log_context_creation(self):
        """Create with all fields explicitly set."""
        ctx = LogContext(
            request_id="req-001",
            teacher_id="t-001",
            run_id="run-042",
            step=7,
            agent="content_creator",
            timestamp="2026-06-23T12:00:00Z",
        )
        assert ctx.request_id == "req-001"
        assert ctx.teacher_id == "t-001"
        assert ctx.run_id == "run-042"
        assert ctx.step == 7
        assert ctx.agent == "content_creator"
        assert ctx.timestamp == "2026-06-23T12:00:00Z"

    def test_log_context_bind(self):
        """bind() returns a new instance with updated fields; original unchanged."""
        original = LogContext(request_id="req-001", run_id="run-001")
        updated = original.bind(agent="planner", step=3)

        assert updated.request_id == "req-001"
        assert updated.run_id == "run-001"
        assert updated.agent == "planner"
        assert updated.step == 3

        # original is immutable
        assert original.agent is None
        assert original.step is None

    def test_log_context_bind_returns_new_instance(self):
        """bind() always returns a different object."""
        ctx = LogContext(run_id="run-001")
        bound = ctx.bind(step=1)
        assert ctx is not bound

    def test_log_context_serialization(self):
        """model_dump produces a JSON-serializable dict."""
        import json

        ctx = LogContext(
            request_id="req-001",
            teacher_id="t-001",
            run_id="run-042",
            step=7,
            agent="reviewer",
            timestamp="2026-06-23T12:00:00Z",
        )
        data = ctx.model_dump()
        # round-trip through JSON without raising
        serialized = json.dumps(data)
        restored = json.loads(serialized)
        assert restored["request_id"] == "req-001"
        assert restored["step"] == 7
        assert restored["agent"] == "reviewer"
