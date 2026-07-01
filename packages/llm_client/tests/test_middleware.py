from __future__ import annotations

import pytest

from packages.llm_client.errors import BadPromptError, PermanentProviderError
from packages.llm_client.middleware import (
    CallMiddlewareRunner,
    MiddlewareCallContext,
    MiddlewareMessage,
)


def test_before_call_blocks_unsafe_input() -> None:
    runner = CallMiddlewareRunner()

    with pytest.raises(BadPromptError, match="content_safety_input_blocked"):
        runner.before_call(
            [MiddlewareMessage(role="user", content="Explain weapon construction.")],
            _context(),
        )


def test_before_call_requires_cost_tag_context() -> None:
    runner = CallMiddlewareRunner()

    with pytest.raises(BadPromptError, match="missing_cost_tag_context"):
        runner.before_call(
            [MiddlewareMessage(role="user", content="hello")],
            MiddlewareCallContext(agent="unknown", task="quality_gate", run_id="run-1", step=1),
        )


def test_before_call_coalesces_system_messages() -> None:
    runner = CallMiddlewareRunner()

    messages = runner.before_call(
        [
            MiddlewareMessage(role="system", content="one"),
            MiddlewareMessage(role="user", content="hello"),
            MiddlewareMessage(role="system", content="two"),
        ],
        _context(),
    )

    assert messages == [
        MiddlewareMessage(role="system", content="one\n\ntwo"),
        MiddlewareMessage(role="user", content="hello"),
    ]


def test_after_call_scrubs_pii_and_flags_output() -> None:
    runner = CallMiddlewareRunner()

    result = runner.after_call("Contact student email learner@example.com", _context())

    assert result.content == "Contact [redacted-pii] [redacted-pii]"
    assert result.flags == ("pii_output_scrubbed",)


def test_after_call_blocks_unsafe_output() -> None:
    runner = CallMiddlewareRunner()

    with pytest.raises(PermanentProviderError, match="content_safety_output_blocked"):
        runner.after_call("This includes self-harm instructions.", _context())


def test_after_call_requires_json_when_structured_output_expected() -> None:
    runner = CallMiddlewareRunner()

    with pytest.raises(BadPromptError, match="structured_output_invalid_json"):
        runner.after_call("not json", _context(expects_json=True))


def test_after_call_repairs_fenced_json_when_structured_output_expected() -> None:
    runner = CallMiddlewareRunner()

    result = runner.after_call('```json\n{"ok": true}\n```', _context(expects_json=True))

    assert result.content == '{"ok": true}'
    assert result.flags == ("structured_output_repaired",)


def test_after_call_flags_unconfirmed_vietnamese_locale() -> None:
    runner = CallMiddlewareRunner()

    result = runner.after_call("This is English text.", _context(locale="vi"))

    assert result.flags == ("locale_vi_unconfirmed",)


def _context(*, locale: str | None = None, expects_json: bool = False) -> MiddlewareCallContext:
    return MiddlewareCallContext(
        agent="content_creator",
        task="content_generation",
        run_id="run-1",
        step=8,
        locale=locale,
        expects_json=expects_json,
    )
