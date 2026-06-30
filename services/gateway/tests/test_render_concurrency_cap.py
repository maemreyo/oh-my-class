from __future__ import annotations

import sys
import time
from typing import AsyncGenerator

import anyio
import pytest

from services.gateway.renderer_adapter import RendererConfig, render_artifact_content
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


class TestRenderConcurrencyCap:
    async def test_concurrent_renders_respect_configured_cap(self) -> None:
        script = """
import json, sys, time
for line in sys.stdin:
    time.sleep(0.25)
    print(json.dumps({'ok': True, 'html': '<!DOCTYPE html><html><body>oh-my-class capped</body></html>'}), flush=True)
"""
        config = RendererConfig(
            command=(sys.executable, "-c", script),
            pool_size=2,
            max_concurrent_renders=1,
        )

        started_at = time.perf_counter()
        html_values: list[str] = []

        async def render_once() -> None:
            html_values.append(await render_artifact_content(VALID_ARTIFACT, config))

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(render_once)
            task_group.start_soon(render_once)
        elapsed = time.perf_counter() - started_at

        assert all("capped" in html for html in html_values)
        assert elapsed >= 0.45
