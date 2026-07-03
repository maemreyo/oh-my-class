"""Step 12 — Finalize: render standalone HTML and persist exports."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from packages.agents.gates.artifact_extract import extract_external_urls
from packages.agents.nodes.state import NodeState

_RENDERER_DIR = "packages/renderer"


def _build_renderer() -> None:
    """Build the renderer once. Called once per finalize run, not per artifact."""
    subprocess.run(
        ["pnpm", "--dir", _RENDERER_DIR, "build"],
        check=True,
        capture_output=True,
        text=True,
    )


def _render_artifact_with_renderer(artifact: dict[str, Any]) -> str:
    """Render a single artifact to HTML via the pre-built renderer."""
    result = subprocess.run(
        ["node", f"{_RENDERER_DIR}/dist/agent-renderer.js"],
        input=json.dumps(artifact),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _check_no_external_urls(artifact: dict[str, Any]) -> list[str]:
    """Return error strings for any external URLs in student-facing content.

    Delegates to ``extract_external_urls`` which scans both ``section.content``
    strings and nested component dicts — covering component-first artifacts
    that have no ``section.content`` at all.
    """
    urls = extract_external_urls(artifact)
    return [f"External URL found in student content: {url}" for url in urls]


def step_12_finalize(state: NodeState) -> dict[str, Any]:
    """Render artifacts to standalone HTML and record exported files."""
    artifacts = state.get("artifacts") or []
    export_formats = state.get("export_formats") or ["html"]

    exported_files: list[dict[str, Any]] = []
    errors: list[str] = []

    if "html" in export_formats:
        # Build renderer ONCE before iterating artifacts.
        _build_renderer()

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
