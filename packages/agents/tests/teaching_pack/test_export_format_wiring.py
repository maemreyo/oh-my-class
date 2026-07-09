from __future__ import annotations

import pytest

from packages.agents.teaching_pack.exporters import ExporterRegistry, UnsupportedExportFormatError
from packages.agents.teaching_pack.nodes import TeachingPackState, _export_finalize


def _approved_state(export_formats: list[str]) -> TeachingPackState:
    return TeachingPackState(
        run_id="run-export",
        teacher_approved=True,
        approved_snapshot_ids=["snap-lesson"],
        contract={"export_formats": export_formats, "topic": "Fractions", "subject": "math"},
        rendered_snapshots=[{
            "snapshot_id": "snap-lesson",
            "artifact_id": "lesson-1",
            "artifact_type": "lesson",
            "content_json": {
                "artifact_id": "lesson-1",
                "artifact_type": "lesson",
                "title": "Equivalent Fractions",
                "sections": [{"title": "Intro", "content": "Compare equal fractions."}],
            },
        }],
    )


class TestTeachingPackExportFormatWiring:
    def test_export_finalize_emits_requested_html_gift_and_qti_files(self) -> None:
        result = _export_finalize(_approved_state(["html", "gift", "qti"]))

        assert result.get("exported_files") == [
            "exports/run-export/snap-lesson.html",
            "exports/run-export/run-export.gift.txt",
            "exports/run-export/run-export.qti.xml",
        ]

    def test_html_only_export_behaves_as_before(self) -> None:
        result = _export_finalize(_approved_state(["html"]))

        assert result.get("exported_files") == ["exports/run-export/snap-lesson.html"]

    def test_export_uses_approval_gate_snapshots_after_resume(self) -> None:
        state = _approved_state(["html"])
        state["approval_gate"] = {"rendered_snapshots": state["rendered_snapshots"]}
        state["rendered_snapshots"] = None
        state["quality_recovery_route"] = "teacher_approval"
        state["quality_issues"] = ["fact_check: uncertain"]
        state["escalate"] = True

        result = _export_finalize(state)

        assert result.get("exported_files") == ["exports/run-export/snap-lesson.html"]
        assert result.get("quality_recovery_route") == ""
        assert result.get("quality_issues") == []
        assert result.get("escalate") is False

    def test_registry_fails_closed_for_unsupported_google_forms(self) -> None:
        with pytest.raises(UnsupportedExportFormatError, match="google_forms"):
            _export_finalize(_approved_state(["google_forms"]))

    def test_every_export_format_is_registered_or_explicitly_unsupported(self) -> None:
        registry = ExporterRegistry.default()

        assert registry.supports("html")
        assert registry.supports("gift")
        assert registry.supports("h5p")
        assert registry.supports("qti")
        assert registry.supports("pptx")
        assert registry.is_explicitly_unsupported("google_forms")

    def test_export_finalize_emits_requested_pptx_file_for_slide_deck_snapshot(self) -> None:
        state = TeachingPackState(
            run_id="run-export",
            teacher_approved=True,
            approved_snapshot_ids=["snap-deck"],
            contract={"export_formats": ["html", "pptx"], "topic": "Fractions", "subject": "math"},
            rendered_snapshots=[{
                "snapshot_id": "snap-deck",
                "artifact_id": "deck-1",
                "artifact_type": "slide_deck",
                "content_json": {"artifact_id": "deck-1", "artifact_type": "slide_deck", "title": "Fractions Deck"},
            }],
        )

        result = _export_finalize(state)

        assert result.get("exported_files") == [
            "exports/run-export/snap-deck.html",
            "exports/run-export/snap-deck.pptx",
        ]

    def test_pptx_export_skips_non_slide_deck_snapshots(self) -> None:
        result = _export_finalize(_approved_state(["pptx"]))

        # _approved_state's fixture snapshot is artifact_type "lesson" — pptx
        # only converts slide_deck content, so no pptx file is produced for it.
        assert result.get("exported_files") == ["exports/run-export/snap-lesson.html"]
