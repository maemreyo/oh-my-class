"""Unit packager HTML bundling tests."""

from __future__ import annotations

import pytest

from packages.exporters.unit_packager import SessionExportResult, UnitPackager


def _make_sessions(n: int, all_approved: bool = True) -> list[SessionExportResult]:
    return [
        SessionExportResult(
            session_id=f"s{i}",
            session_index=i,
            title=f"Session {i} Title",
            html_content=f"<p>Session {i} content</p>",
            is_approved=all_approved,
            is_included=all_approved,
        )
        for i in range(1, n + 1)
    ]


def _seq_data(topic: str = "Test Unit", theme: str = "default") -> dict:
    return {
        "topic": topic,
        "theme": theme,
        "sessions": [
            {"order_index": i, "title": f"S{i}", "bloom_level_primary": "understand", "methodology_primary": "concept_map", "prerequisite_sessions": []}
            for i in range(1, 4)
        ],
    }


class TestHtmlBundling:
    def test_3_sessions_produces_html_with_cover_toc_content(self) -> None:
        sessions = _make_sessions(3)
        packager = UnitPackager(sessions, _seq_data(), theme="default")
        html = packager.build_html_bundle()

        assert "<!DOCTYPE html>" in html
        assert "Test Unit" in html
        assert "Table of Contents" in html
        assert "Session 1 Title" in html
        assert "Session 2 Title" in html
        assert "Session 3 Title" in html
        assert "<p>Session 1 content</p>" in html

    def test_html_includes_sequence_overview(self) -> None:
        sessions = _make_sessions(2)
        packager = UnitPackager(sessions, _seq_data())
        html = packager.build_html_bundle()
        assert "Session Sequence" in html

    def test_html_includes_theme_token(self) -> None:
        sessions = _make_sessions(2)
        packager = UnitPackager(sessions, _seq_data(theme="forest"))
        html = packager.build_html_bundle()
        assert "forest" in html

    def test_html_partial_includes_warning(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "Session 1", "<p>S1</p>", True, True),
            SessionExportResult("s2", 2, "Session 2", "<p>S2</p>", True, True),
            SessionExportResult("s3", 3, "Session 3 (not approved)", None, False, False),
        ]
        packager = UnitPackager(sessions, _seq_data())
        html = packager.build_html_bundle()
        assert "2/3" in html
        assert "approved sessions included" in html

    def test_html_does_not_include_unapproved_sessions(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "Session 1", "<p>S1</p>", True, True),
            SessionExportResult("s2", 2, "Excluded Session", "<p>excluded</p>", False, False),
        ]
        packager = UnitPackager(sessions, _seq_data())
        html = packager.build_html_bundle()
        assert "Excluded Session" not in html
        assert "Session 1" in html
