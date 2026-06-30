"""Tests for the gateway-to-Eta renderer adapter.

The adapter spawns the TypeScript renderer as a subprocess, pipes artifact
content JSON via stdin, and reads rendered HTML from stdout.  Tests use
lightweight shell mocks — no real renderer build required.
"""
from __future__ import annotations

import sys

import pytest

from services.gateway.renderer_adapter import (
    RendererAdapterError,
    RendererConfig,
    render_artifact_content,
)

# ── Fixture: mock commands ───────────────────────────────────────────────────

MOCK_SUCCESS = [
    sys.executable,
    "-c",
    "import sys; sys.stdout.write('<!DOCTYPE html><html><body>oh-my-class</body></html>')",
]
MOCK_NONZERO_EXIT = [sys.executable, "-c", "import sys; sys.exit(1)"]
MOCK_MALFORMED_OUTPUT = [
    sys.executable,
    "-c",
    "import sys; sys.stdout.write('not html at all')",
]
MOCK_HUNG = [
    sys.executable,
    "-c",
    "import time; time.sleep(999)",
]
MOCK_DIRTY_OUTPUT = [
    sys.executable,
    "-c",
    (
        "import sys; sys.stdout.write("
        "'<!DOCTYPE html><html><head>"
        '<link href="https://cdn.example.com/style.css">'
        "</head><body>oh-my-class</body></html>')"
    ),
]

VALID_ARTIFACT: dict[str, object] = {
    "artifact_type": "lesson",
    "title": "Fraction Basics",
    "metadata": {"subject": "Math", "grade_level": "Grade 5"},
    "sections": [{"title": "Intro", "content": "What is a fraction?"}],
}


def _config(command: list[str], *, timeout: float = 5.0) -> RendererConfig:
    return RendererConfig(command=tuple(command), timeout_seconds=timeout, backend="subprocess")


# ── Test: success ────────────────────────────────────────────────────────────


class TestRenderSuccess:
    async def test_returns_html_on_exit_zero(self) -> None:
        """Given a renderer that exits 0 with valid HTML, the adapter returns the HTML."""
        html = await render_artifact_content(VALID_ARTIFACT, _config(MOCK_SUCCESS))
        assert html == "<!DOCTYPE html><html><body>oh-my-class</body></html>"

    async def test_passes_json_via_stdin(self) -> None:
        """Given valid artifact content, the adapter writes valid JSON to stdin."""
        # Mock: reads JSON stdin, echoes title in standalone HTML wrapper
        echo_cmd = [
            sys.executable,
            "-c",
            (
                "import sys, json; data = json.load(sys.stdin); "
                "t = data.get('title', ''); "
                "sys.stdout.write(f'<!DOCTYPE html><html><body>{t}</body></html>')"
            ),
        ]
        result = await render_artifact_content(VALID_ARTIFACT, _config(echo_cmd))
        assert "Fraction Basics" in result


# ── Test: nonzero exit ───────────────────────────────────────────────────────


class TestNonzeroExit:
    async def test_raises_error_on_nonzero_exit(self) -> None:
        """Given a renderer that exits non-zero, the adapter raises RendererAdapterError."""
        with pytest.raises(RendererAdapterError, match="exit code 1"):
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_NONZERO_EXIT))

    async def test_error_carries_exit_code(self) -> None:
        """Given a non-zero exit, the error carries the actual exit code."""
        with pytest.raises(RendererAdapterError) as exc_info:
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_NONZERO_EXIT))
        assert exc_info.value.exit_code == 1

    async def test_error_code_is_pipeline_error(self) -> None:
        """Given a non-zero exit, the error uses PIPELINE_ERROR code."""
        with pytest.raises(RendererAdapterError) as exc_info:
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_NONZERO_EXIT))
        assert exc_info.value.error_code == "PIPELINE_ERROR"


# ── Test: malformed / unexpected output ──────────────────────────────────────


class TestMalformedOutput:
    async def test_raises_error_on_non_html_output(self) -> None:
        """Given a renderer that outputs non-HTML text, the adapter raises RendererAdapterError."""
        with pytest.raises(RendererAdapterError, match="invalid output"):
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_MALFORMED_OUTPUT))


# ── Test: timeout ────────────────────────────────────────────────────────────


class TestTimeout:
    async def test_raises_error_on_timeout(self) -> None:
        """Given a hung renderer and a short timeout, the adapter raises RendererAdapterError."""
        with pytest.raises(RendererAdapterError, match="timed out"):
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_HUNG, timeout=0.5))

    async def test_timeout_default_is_30s(self) -> None:
        """The default RendererConfig timeout is 30 seconds."""
        config = RendererConfig()
        assert config.timeout_seconds == 30.0


# ── Test: no external assets ────────────────────────────────────────────────


class TestNoExternalAssets:
    async def test_rejects_output_with_cdn_references(self) -> None:
        """Given CDN links in output, the adapter raises RendererAdapterError."""
        with pytest.raises(RendererAdapterError, match="external assets"):
            await render_artifact_content(VALID_ARTIFACT, _config(MOCK_DIRTY_OUTPUT))

    async def test_accepts_standalone_html(self) -> None:
        """Given clean standalone HTML, the adapter returns it without error."""
        html = await render_artifact_content(VALID_ARTIFACT, _config(MOCK_SUCCESS))
        assert "cdn" not in html.lower()
        assert "https://" not in html


# ── Test: RendererConfig defaults ────────────────────────────────────────────


class TestRendererConfig:
    def test_default_command(self) -> None:
        """The default command targets the compiled agent-renderer."""
        config = RendererConfig()
        assert "agent-renderer" in " ".join(config.command)

    def test_custom_command(self) -> None:
        """A custom command overrides the default."""
        config = RendererConfig(command=("echo", "hello"), timeout_seconds=10.0)
        assert config.command == ("echo", "hello")
        assert config.timeout_seconds == 10.0

    def test_frozen_dataclass(self) -> None:
        """RendererConfig is immutable."""
        config = RendererConfig()
        with pytest.raises(AttributeError):
            config.timeout_seconds = 999  # type: ignore[misc]
