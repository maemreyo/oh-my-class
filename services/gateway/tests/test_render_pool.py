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


def worker_command(script: str) -> tuple[str, ...]:
    return (sys.executable, "-c", script)


class TestRenderPoolReuse:
    async def test_reuses_one_worker_for_multiple_renders(self, tmp_path: Path) -> None:
        starts_path = tmp_path / "starts.txt"
        script = f"""
import json, pathlib, sys
path = pathlib.Path({str(starts_path)!r})
path.write_text(path.read_text() + 'x' if path.exists() else 'x')
for line in sys.stdin:
    request = json.loads(line)
    title = request['artifact']['title']
    print(json.dumps({{'ok': True, 'html': f'<!DOCTYPE html><html><body>oh-my-class {{title}}</body></html>'}}), flush=True)
"""
        config = RendererConfig(
            command=worker_command(script),
            pool_size=1,
            max_concurrent_renders=1,
        )

        rendered = [await render_artifact_content(VALID_ARTIFACT, config) for _ in range(3)]

        assert all("Fraction Basics" in html for html in rendered)
        assert starts_path.read_text() == "x"


class TestRenderVersionPin:
    async def test_version_mismatch_fails_fast(self) -> None:
        config = RendererConfig(renderer_version="stale-renderer")

        with pytest.raises(RendererAdapterError, match="renderer_version mismatch"):
            await render_artifact_content(VALID_ARTIFACT, config)

    async def test_schema_violation_fails_fast(self) -> None:
        config = RendererConfig()
        invalid_artifact: dict[str, object] = {
            "artifact_type": "lesson",
            "title": "No Sections",
        }

        with pytest.raises(RendererAdapterError, match="sections"):
            await render_artifact_content(invalid_artifact, config)
