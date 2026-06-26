"""Step 12 — Finalize: render standalone HTML and persist exports."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from packages.agents.state import (
    OhMyClassState,  # noqa: TC001  needed at runtime for LangGraph get_type_hints
)

_EXTERNAL_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
_RENDERER_DIR = "packages/renderer"


def _render_artifact_with_renderer(artifact: dict[str, Any]) -> str:
    subprocess.run(
        ["pnpm", "--dir", _RENDERER_DIR, "build"],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["node", f"{_RENDERER_DIR}/dist/agent-renderer.js"],
        input=json.dumps(artifact),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _check_no_external_urls(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sections = artifact.get("sections") or []
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        if section.get("teacher_only"):
            continue
        content = section.get("content", "")
        if isinstance(content, str):
            match = _EXTERNAL_URL_PATTERN.search(content)
            if match:
                errors.append(
                    f"Section[{i}] contains external URL: {match.group()}"
                )
    return errors


def step_12_finalize(state: OhMyClassState) -> dict[str, Any]:
    """Render artifacts to standalone HTML and record exported files."""
    artifacts = state.get("artifacts") or []
    export_formats = state.get("export_formats") or ["html"]

    exported_files: list[dict[str, Any]] = []
    errors: list[str] = []

    if "html" in export_formats:
        for i, artifact in enumerate(artifacts):
            if artifact.get("teacher_only"):
                continue

            invariant_violations = _check_no_external_urls(artifact)
            if invariant_violations:
                errors.extend(invariant_violations)
                continue

            rendered_html = _render_artifact_with_renderer(artifact)
            artifact_id = artifact.get(
                "artifact_id", f"artifact-{i}"
            )
            title = artifact.get("title", f"Artifact {i}")

            exported_files.append({
                "artifact_id": artifact_id,
                "format": "html",
                "title": title,
                "content": rendered_html,
                "artifact_type": artifact.get(
                    "artifact_type", "unknown"
                ),
                "theme": artifact.get("theme", "default"),
            })

    if errors:
        return {
            "exported_files": exported_files,
            "current_step": 12,
            "export_ready": False,
            "fail_layer": "export",
            "fail_type": "invariant",
            "fail_count": state.get("fail_count", 0),
            "fail_context": {"errors": errors},
        }

    return {
        "exported_files": exported_files,
        "current_step": 12,
    }
