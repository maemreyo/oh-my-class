"""Gateway adapter that invokes the TypeScript Eta renderer over stdin/stdout."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from services.gateway.renderer_models import RendererAdapterError, RendererConfig
from services.gateway.renderer_pool import pool_for

# ── Config ───────────────────────────────────────────────────────────────────

_CSS_EXTERNAL_PATTERN = re.compile(
    r"(?:@import\s+url\(|url\()\s*['\"]?(?:https?://|//)",
    re.IGNORECASE,
)
_EXTERNAL_SCRIPT_PATTERN = re.compile(
    r"<script\b[^>]*\bsrc\s*=\s*['\"]https?://", re.IGNORECASE
)
_EXTERNAL_LINK_PATTERN = re.compile(
    r'<link\b[^>]*\bhref\s*=\s*["\']https?://', re.IGNORECASE
)


def _validate_standalone_html(rendered_html: str) -> str | None:
    """Validate that rendered output is standalone HTML.

    Returns ``None`` when valid; otherwise returns a reason string describing
    the first validation failure found.
    """
    lowered = rendered_html.lower()
    if "<!doctype html" not in lowered:
        return "output is not standalone HTML (missing DOCTYPE)"
    if _CSS_EXTERNAL_PATTERN.search(rendered_html):
        return "renderer output contains external assets (CSS import/url)"
    if _EXTERNAL_SCRIPT_PATTERN.search(rendered_html):
        return "renderer output contains external assets (script src)"
    if _EXTERNAL_LINK_PATTERN.search(rendered_html):
        return "renderer output contains external assets (link href)"
    return None


def validate_rendered_html(stdout_text: str, exit_code: int | None) -> str:
    if not stdout_text.strip():
        raise RendererAdapterError("Renderer subprocess produced invalid output (empty)", exit_code=exit_code)
    validation_failure = _validate_standalone_html(stdout_text)
    if validation_failure is not None:
        raise RendererAdapterError(
            f"Renderer produced invalid output: {validation_failure}",
            exit_code=exit_code,
        )
    return stdout_text


# ── Adapter entry point ──────────────────────────────────────────────────────

async def render_artifact_content(
    artifact_content: dict[str, Any],
    config: RendererConfig | None = None,
) -> str:
    """Render artifact content to standalone HTML via the TypeScript renderer.

    Sends ``artifact_content`` as JSON to the renderer subprocess's stdin,
    reads HTML from stdout, and validates the output.

    Args:
        artifact_content: Artifact content dict (JSON-serializable).
        config: Renderer configuration (command, timeout).  Uses defaults
            when ``None``.

    Returns:
        Rendered HTML string.

    Raises:
        RendererAdapterError: On subprocess failure, timeout, or invalid output.
    """
    cfg = config or RendererConfig()
    if cfg.backend == "pool":
        return await pool_for(cfg).render(artifact_content)

    json_bytes = json.dumps(artifact_content, ensure_ascii=False).encode("utf-8")

    try:
        process = await asyncio.create_subprocess_exec(
            *cfg.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input=json_bytes),
                timeout=cfg.timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise RendererAdapterError(
                f"Renderer subprocess timed out after {cfg.timeout_seconds}s",
            ) from None

    except (OSError, ValueError) as exc:
        raise RendererAdapterError(
            f"Failed to start renderer process: {exc}",
        ) from exc

    exit_code = process.returncode
    stdout_text = stdout_bytes.decode("utf-8") if stdout_bytes else ""
    stderr_text = stderr_bytes.decode("utf-8") if stderr_bytes else ""

    if exit_code != 0:
        raise RendererAdapterError(
            f"Renderer subprocess failed with exit code {exit_code}",
            exit_code=exit_code,
            stderr=stderr_text or None,
        )

    return validate_rendered_html(stdout_text, exit_code)
