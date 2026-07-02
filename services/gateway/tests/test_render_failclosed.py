from __future__ import annotations

import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest

from services.gateway.renderer_adapter import RendererAdapterError, RendererConfig, render_artifact_content
from services.gateway.renderer_pool import close_renderer_pools


VALID_ARTIFACT: dict[str, object] = {
    "artifact_type": "lesson",
    "title": "Fraction Basics",
    "metadata": {"subject": "Math", "grade_level": "Grade 5"},
    "sections": [{"title": "Intro", "content": "What is a fraction?"}],
}


@pytest.fixture(autouse=True)
async def clean_renderer_pools() -> AsyncGenerator[None, None]:
    await close_renderer_pools()
    yield
    await close_renderer_pools()


class TestRenderFailClosed:
    async def test_renderer_error_captures_stderr(self) -> None:
        script = """
import json, sys
for line in sys.stdin:
    print(json.dumps({'ok': False, 'error': 'render crash', 'stderr': 'stack trace'}), flush=True)
"""
        config = RendererConfig(command=(sys.executable, "-c", script), max_retries=0)

        with pytest.raises(RendererAdapterError, match="render crash") as exc_info:
            await render_artifact_content(VALID_ARTIFACT, config)

        assert exc_info.value.stderr == "stack trace"

    async def test_transient_worker_failure_retries_once(self, tmp_path: Path) -> None:
        marker = tmp_path / "transient-marker"
        script = f"""
import json, pathlib, sys
path = pathlib.Path({str(marker)!r})
if not path.exists():
    path.write_text('failed')
    sys.stderr.write('temporary boot failure')
    sys.exit(1)
for line in sys.stdin:
    print(json.dumps({{'ok': True, 'html': '<!DOCTYPE html><html><body>oh-my-class retry ok</body></html>'}}), flush=True)
"""
        config = RendererConfig(command=(sys.executable, "-c", script), max_retries=1, pool_size=1)

        html = await render_artifact_content(VALID_ARTIFACT, config)

        assert "retry ok" in html

    async def test_typed_non_retryable_worker_error_does_not_retry(self, tmp_path: Path) -> None:
        attempts_path = tmp_path / "attempts.txt"
        script = f"""
import json, pathlib, sys
path = pathlib.Path({str(attempts_path)!r})
path.write_text(path.read_text() + 'x' if path.exists() else 'x')
for line in sys.stdin:
    print(json.dumps({{'ok': False, 'error': {{'code': 'validation_failed', 'category': 'validation', 'retryable': False, 'message': 'invalid fixture'}}}}), flush=True)
"""
        config = RendererConfig(command=(sys.executable, "-c", script), max_retries=2, pool_size=1)

        with pytest.raises(RendererAdapterError, match="invalid fixture") as exc_info:
            await render_artifact_content(VALID_ARTIFACT, config)

        assert exc_info.value.retryable is False
        assert exc_info.value.renderer_code == "validation_failed"
        assert attempts_path.read_text() == "x"

    async def test_typed_retryable_worker_error_retries_once(self, tmp_path: Path) -> None:
        attempts_path = tmp_path / "retryable-attempts.txt"
        script = f"""
import json, pathlib, sys
path = pathlib.Path({str(attempts_path)!r})
attempts = len(path.read_text()) if path.exists() else 0
path.write_text('x' * (attempts + 1))
for line in sys.stdin:
    if attempts == 0:
        print(json.dumps({{'ok': False, 'error': {{'code': 'internal_error', 'category': 'internal', 'retryable': True, 'message': 'temporary internal'}}}}), flush=True)
    else:
        print(json.dumps({{'ok': True, 'html': '<!DOCTYPE html><html><body>oh-my-class typed retry ok</body></html>'}}), flush=True)
"""
        config = RendererConfig(command=(sys.executable, "-c", script), max_retries=1, pool_size=1)

        html = await render_artifact_content(VALID_ARTIFACT, config)

        assert "typed retry ok" in html
        assert attempts_path.read_text() == "xx"
