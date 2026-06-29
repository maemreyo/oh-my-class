from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from packages.agents.teaching_pack.nodes import JsonObject
from packages.agents.teaching_pack.nodes import TeachingPackState, _render_quality
from services.gateway.teaching_pack_export_writer import FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_types import RunId
from tests.e2e.rich_teaching_pack_fixtures import minimal_shell_artifact, rich_artifacts

ANSWER_MARKERS = ("Answer key", "Correct answer", "Answer:", "Correct:", "Solution:")


def _rendered_snapshots(state: TeachingPackState) -> list[JsonObject]:
    assert "rendered_snapshots" in state
    return state["rendered_snapshots"]


def _export_state(snapshots: list[JsonObject]) -> JsonObject:
    return cast(
        "JsonObject",
        {
            "rendered_snapshots": snapshots,
            "approved_snapshot_ids": [str(snapshot["snapshot_id"]) for snapshot in snapshots],
        },
    )


def _assert_student_html(html: str) -> None:
    assert "<!DOCTYPE html" in html
    assert "oh-my-class" in html
    assert "http://" not in html
    assert "https://" not in html
    for marker in ANSWER_MARKERS:
        assert marker not in html


def _visible_content_blocks(html: str) -> int:
    return html.count("<section") + html.count("<article") + html.count("<li")


def _assert_rich_html(html: str, artifact_type: str) -> None:
    _assert_student_html(html)
    assert f"artifact--{artifact_type}" in html
    assert len(html) > 4_000
    assert _visible_content_blocks(html) >= 4


def test_minimal_shell_fixture_is_not_assessable() -> None:
    artifact = minimal_shell_artifact()

    result = _render_quality(TeachingPackState(run_id="minimal-shell", artifacts=[artifact]))
    student_html = str(_rendered_snapshots(result)[0]["student_rendered_html"])

    _assert_student_html(student_html)
    assert _visible_content_blocks(student_html) < 4


@pytest.mark.asyncio
async def test_rich_active_artifacts_render_and_export_through_existing_renderer(tmp_path: Path) -> None:
    run_id = "component-driven-rich-pack"
    artifacts = rich_artifacts()

    result = _render_quality(TeachingPackState(run_id=run_id, artifacts=artifacts))
    snapshots = _rendered_snapshots(result)
    writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path)

    exported_files = await writer.write_exports(
        RunId(run_id),
        _export_state(snapshots),
    )

    assert len(exported_files) == len(artifacts)
    for export_path, artifact in zip(exported_files, artifacts, strict=True):
        html = Path(export_path).read_text(encoding="utf-8")
        _assert_rich_html(html, str(artifact["artifact_type"]))


@pytest.mark.asyncio
async def test_scoped_regenerated_rich_artifact_preserves_accepted_export(tmp_path: Path) -> None:
    run_id = "component-driven-scoped"
    accepted, rejected = rich_artifacts()[0], rich_artifacts()[2]
    regenerated = {**rejected, "artifact_id": "quiz-regenerated-rich", "title": "Regenerated Equivalent Fractions Quiz"}

    result = _render_quality(TeachingPackState(run_id=run_id, artifacts=[accepted, regenerated]))
    snapshots = _rendered_snapshots(result)
    writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path)
    exported_files = await writer.write_exports(
        RunId(run_id),
        _export_state(snapshots),
    )

    exported_html = [Path(path).read_text(encoding="utf-8") for path in exported_files]
    assert any("Learning Targets" in html for html in exported_html)
    assert any("Regenerated Equivalent Fractions Quiz" in html for html in exported_html)
    for html in exported_html:
        _assert_student_html(html)
