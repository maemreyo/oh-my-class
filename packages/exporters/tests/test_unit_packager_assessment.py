"""Unit packager assessment (zip) bundling tests."""

from __future__ import annotations

import io
import json
import zipfile

from packages.exporters.unit_packager import SessionExportResult, UnitPackager


def _sessions(n: int) -> list[SessionExportResult]:
    return [
        SessionExportResult(f"s{i}", i, f"Session {i}", f"// S{i}", True, True)
        for i in range(1, n + 1)
    ]


_SEQ = {"topic": "Unit", "theme": "default", "sessions": []}


class TestAssessmentZip:
    def test_zip_contains_per_session_files_plus_manifest(self) -> None:
        sessions = _sessions(3)
        packager = UnitPackager(sessions, _SEQ)
        zip_bytes = packager.build_assessment_zip("gift")

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()

        session_files = [n for n in names if n.endswith(".gift")]
        assert len(session_files) == 3
        assert "unit_manifest.json" in names

    def test_zip_manifest_is_valid_json(self) -> None:
        sessions = _sessions(2)
        packager = UnitPackager(sessions, {"topic": "My Unit", "sessions": []})
        zip_bytes = packager.build_assessment_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest_raw = zf.read("unit_manifest.json")

        manifest = json.loads(manifest_raw)
        assert "topic" in manifest
        assert "total_sessions" in manifest
        assert "included" in manifest
        assert manifest["total_sessions"] == 2

    def test_zip_files_independently_valid(self) -> None:
        sessions = _sessions(3)
        packager = UnitPackager(sessions, _SEQ)
        zip_bytes = packager.build_assessment_zip()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if name != "unit_manifest.json":
                    content = zf.read(name)
                    assert len(content) > 0, f"{name} should not be empty"

    def test_zip_manifest_omitted_sessions_listed(self) -> None:
        sessions = [
            SessionExportResult("s1", 1, "S1", "c1", True, True),
            SessionExportResult("s2", 2, "S2", None, False, False),
        ]
        packager = UnitPackager(sessions, _SEQ)
        zip_bytes = packager.build_assessment_zip()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            manifest = json.loads(zf.read("unit_manifest.json"))
        assert len(manifest["omitted"]) == 1
        assert manifest["omitted"][0]["session_id"] == "s2"
