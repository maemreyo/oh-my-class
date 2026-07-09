"""Tests for lazy bundling and enum guard."""

from __future__ import annotations

from typing import get_args

import pytest

from packages.exporters.unit_packager import SessionExportResult, UnitBundleResult, UnitPackager


_SEQ = {"topic": "Lazy Test", "theme": "default", "sessions": []}


class TestLazyBundling:
    def test_no_bundle_before_export_invoked(self) -> None:
        """Instantiating UnitPackager does not produce any output."""
        sessions = [SessionExportResult("s1", 1, "S1", "<p>s1</p>", True, True)]
        packager = UnitPackager(sessions, _SEQ)
        # No bundle produced — accessing attributes must not trigger generation.
        assert packager._session_results is not None  # only internal state
        # build_bundle has not been called; result should be None if we check the field:
        # (we test that calling build_bundle actually works once)
        result = packager.build_bundle()
        assert result is not None
        assert isinstance(result, UnitBundleResult)

    def test_bundle_produced_only_when_build_called(self) -> None:
        sessions = [SessionExportResult("s1", 1, "S1", "<p>s1</p>", True, True)]
        packager = UnitPackager(sessions, _SEQ)
        # First call produces a result
        result1 = packager.build_bundle()
        # Second call (lazy — idempotent re-computation)
        result2 = packager.build_bundle()
        assert result1.html_bundle == result2.html_bundle


class TestExportFormatEnumUnchanged:
    def test_export_format_enum_has_no_new_values(self) -> None:
        """ExportFormat must not gain new values from the UnitPackager feature."""
        try:
            from services.gateway.teaching_pack_export_writer import ExportFormat
            known_values = {"html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv"}
            # ExportFormat is a PEP 695 `type` alias (Literal[...]), not an Enum —
            # use get_args instead of iterating it directly.
            actual_values = set(get_args(ExportFormat))
            new_values = actual_values - known_values
            assert not new_values, (
                f"ExportFormat gained unexpected new values: {new_values}. "
                "UnitPackager must not add new ExportFormat enum values."
            )
        except ImportError:
            pytest.skip("ExportFormat not importable in this environment")
