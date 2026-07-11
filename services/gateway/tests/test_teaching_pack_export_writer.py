from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from services.gateway.teaching_pack_export_writer import ExportAdapterError, FileSystemTeachingPackExportWriter
from services.gateway.teaching_pack_types import JsonObject, RunId


@dataclass(frozen=True, slots=True)
class RecordingRenderer:
    rendered_html: str = "<!DOCTYPE html><html><body>oh-my-class export</body></html>"
    calls: list[JsonObject] = field(default_factory=list)

    async def render(self, artifact: JsonObject) -> str:
        self.calls.append(artifact)
        return self.rendered_html


class TestTeachingPackExportWriter:
    @pytest.mark.anyio
    async def test_filesystem_writer_fails_fast_for_unknown_export_format(
        self,
        tmp_path: Path,
    ) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=RecordingRenderer())
        state = {
            "approved_snapshot_ids": ["snapshot-1"],
            "contract": {"export_formats": ["html", "unknown_format"]},
            "rendered_snapshots": [{"snapshot_id": "snapshot-1", "content_json": {"title": "Approved"}}],
        }

        with pytest.raises(ExportAdapterError, match="unknown_format"):
            await writer.write_exports(RunId("run-unknown-export"), state)

    @pytest.mark.anyio
    async def test_filesystem_writer_exports_approved_slide_deck_html(
        self,
        tmp_path: Path,
    ) -> None:
        renderer = RecordingRenderer("<!DOCTYPE html><html><body>oh-my-class slide deck</body></html>")
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
        slide_deck = {
            "artifact_type": "slide_deck",
            "title": "Equivalent Fractions Slide Deck",
            "theme": "default",
            "sections": [{"title": "Deck", "slide_deck": {"deck_id": "deck-1"}}],
            "metadata": {"slide_deck_data": {"deck_id": "deck-1"}},
            "accessibility": {"language": "en"},
        }
        state = {
            "approved_snapshot_ids": ["slide-deck-snapshot"],
            "contract": {"export_formats": ["html"]},
            "rendered_snapshots": [
                {"snapshot_id": "slide-deck-snapshot", "content_json": slide_deck},
            ],
        }

        exported = await writer.write_exports(RunId("run-slide-export"), state)

        assert len(exported) == 1
        export_path = Path(exported[0])
        assert export_path.name == "slide-deck-snapshot.html"
        assert export_path.read_text(encoding="utf-8") == "<!DOCTYPE html><html><body>oh-my-class slide deck</body></html>"
        assert renderer.calls == [slide_deck]

    @pytest.mark.anyio
    async def test_filesystem_writer_exports_release_gate_html_matrix(
        self,
        tmp_path: Path,
    ) -> None:
        renderer = RecordingRenderer("<!DOCTYPE html><html><body>oh-my-class release gate</body></html>")
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path, renderer=renderer)
        artifacts = [
            {
                "snapshot_id": "lesson-snapshot",
                "content_json": {"artifact_id": "lesson-1", "artifact_type": "lesson", "title": "Lesson"},
            },
            {
                "snapshot_id": "slide-deck-snapshot",
                "content_json": {"artifact_id": "slide-1", "artifact_type": "slide_deck", "title": "Slide Deck"},
            },
            {
                "snapshot_id": "quiz-snapshot",
                "content_json": {
                    "artifact_id": "quiz-1",
                    "artifact_type": "quiz",
                    "title": "Quiz",
                    "sections": [
                        {
                            "id": "s1",
                            "questions": [
                                {
                                    "id": "q1",
                                    "type": "multiple_choice_single",
                                    "stem": "What is 2 + 2?",
                                    "options": [
                                        {"id": "a", "text": "3", "isCorrect": False},
                                        {"id": "b", "text": "4", "isCorrect": True},
                                    ],
                                },
                            ],
                        },
                    ],
                },
            },
        ]
        state = {
            "approved_snapshot_ids": ["lesson-snapshot", "slide-deck-snapshot", "quiz-snapshot"],
            # qti is intentionally excluded: the CLI bridge always raises
            # UnsupportedFormatError for it (see packages/exporters/src/qti/qti.ts
            # and its dedicated qti.test.ts/cli.test.ts coverage) until QTI export
            # is actually implemented.
            "contract": {"export_formats": ["html", "gift", "h5p"]},
            "rendered_snapshots": artifacts,
        }

        exported = await writer.write_exports(RunId("run-slide-release"), state)

        assert {Path(path).name for path in exported} == {
            "lesson-snapshot.html",
            "slide-deck-snapshot.html",
            "quiz-snapshot.html",
            "run-slide-release.gift.txt",
            "run-slide-release.h5p",
        }
        assert renderer.calls == [snapshot["content_json"] for snapshot in artifacts]
