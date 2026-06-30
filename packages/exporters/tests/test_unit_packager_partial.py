"""Tests for partial unit bundle (not all sessions approved)."""

from __future__ import annotations

from packages.exporters.unit_packager import SessionExportResult, UnitPackager


_SEQ = {"topic": "Partial Unit", "theme": "default", "sessions": []}


class TestPartialBundle:
    def test_partial_bundle_contains_only_approved_sessions(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "S1", "<p>S1</p>", True, True),
            SessionExportResult("s2", 2, "S2", "<p>S2</p>", True, True),
            SessionExportResult("s3", 3, "S3 (pending)", None, False, False),
        ]
        packager = UnitPackager(sessions, _SEQ)
        result = packager.build_bundle()
        assert result.included_sessions == 2
        assert result.total_sessions == 3

    def test_omitted_sessions_in_result(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "S1", "<p>S1</p>", True, True),
            SessionExportResult("s2", 2, "S2 not done", None, False, False),
        ]
        packager = UnitPackager(sessions, _SEQ)
        result = packager.build_bundle()
        assert len(result.omitted_sessions) == 1
        assert result.omitted_sessions[0]["session_id"] == "s2"

    def test_html_bundle_shows_partial_warning(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "S1", "<p>S1</p>", True, True),
            SessionExportResult("s2", 2, "S2 pending", None, False, False),
        ]
        packager = UnitPackager(sessions, _SEQ)
        html = packager.build_html_bundle()
        assert "1/2" in html  # partial count

    def test_all_sessions_approved_no_omitted(self) -> None:
        sessions = [
            SessionExportResult(f"s{i}", i, f"S{i}", f"<p>S{i}</p>", True, True)
            for i in range(1, 4)
        ]
        packager = UnitPackager(sessions, _SEQ)
        result = packager.build_bundle()
        assert result.omitted_sessions == []
        assert result.included_sessions == 3
