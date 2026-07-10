from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.teaching_pack.nodes import JsonObject
from services.gateway.teaching_pack_export_writer import (
    FileSystemTeachingPackExportWriter,
    _subprocess_formats,
    _unsupported_formats,
)
from services.gateway.teaching_pack_types import RunId


def _state_with_formats(*formats: str) -> JsonObject:
    return cast(
        "JsonObject",
        {
            "contract": {"export_formats": list(formats)},
            "rendered_snapshots": [],
            "approved_snapshot_ids": [],
        },
    )


class TestSubprocessFormatsDispatch:
    def test_gift_h5p_qti_routed_to_subprocess(self) -> None:
        state = _state_with_formats("gift", "h5p", "qti")
        result = _subprocess_formats(state)
        assert result == ["gift", "h5p", "qti"]

    def test_anki_apkg_and_flashcard_tsv_still_subprocess(self) -> None:
        state = _state_with_formats("anki_apkg", "flashcard_tsv")
        result = _subprocess_formats(state)
        assert result == ["anki_apkg", "flashcard_tsv"]

    def test_all_subprocess_formats_combined(self) -> None:
        state = _state_with_formats("gift", "h5p", "qti", "anki_apkg", "flashcard_tsv")
        result = _subprocess_formats(state)
        assert set(result) == {"gift", "h5p", "qti", "anki_apkg", "flashcard_tsv"}

    def test_google_forms_stays_unsupported(self) -> None:
        state = _state_with_formats("google_forms")
        result = _unsupported_formats(state)
        assert result == ["google_forms"]

    def test_empty_export_formats_returns_empty(self) -> None:
        state = cast("JsonObject", {"contract": {}})
        assert _subprocess_formats(state) == []


class TestWriterDispatchesToNodeExport:
    @pytest.mark.asyncio
    async def test_gift_format_calls_node_export(self, tmp_path: Path) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path)
        state = cast(
            "JsonObject",
            {
                "rendered_snapshots": [],
                "approved_snapshot_ids": [],
                "contract": {"export_formats": ["gift"]},
            },
        )
        mock_path = str(tmp_path / "run-1" / "run-1.gift.txt")
        with patch(
            "services.gateway.teaching_pack_export_writer.node_export",
            new_callable=AsyncMock,
            return_value=mock_path,
        ) as mock_export:
            result = await writer.write_exports(RunId("run-1"), state)
            mock_export.assert_called_once()
            assert mock_export.call_args[0][0] == "gift"
            assert mock_path in result

    @pytest.mark.asyncio
    async def test_h5p_format_calls_node_export(self, tmp_path: Path) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path)
        state = cast(
            "JsonObject",
            {
                "rendered_snapshots": [],
                "approved_snapshot_ids": [],
                "contract": {"export_formats": ["h5p"]},
            },
        )
        mock_path = str(tmp_path / "run-2" / "run-2.h5p")
        with patch(
            "services.gateway.teaching_pack_export_writer.node_export",
            new_callable=AsyncMock,
            return_value=mock_path,
        ) as mock_export:
            result = await writer.write_exports(RunId("run-2"), state)
            mock_export.assert_called_once()
            assert mock_export.call_args[0][0] == "h5p"
            assert mock_path in result

    @pytest.mark.asyncio
    async def test_qti_format_calls_node_export(self, tmp_path: Path) -> None:
        writer = FileSystemTeachingPackExportWriter(base_dir=tmp_path)
        state = cast(
            "JsonObject",
            {
                "rendered_snapshots": [],
                "approved_snapshot_ids": [],
                "contract": {"export_formats": ["qti"]},
            },
        )
        mock_path = str(tmp_path / "run-3" / "run-3.qti.xml")
        with patch(
            "services.gateway.teaching_pack_export_writer.node_export",
            new_callable=AsyncMock,
            return_value=mock_path,
        ) as mock_export:
            result = await writer.write_exports(RunId("run-3"), state)
            mock_export.assert_called_once()
            assert mock_export.call_args[0][0] == "qti"
            assert mock_path in result


class TestInlinePayloadBuildersRemoved:
    def test_no_gift_payload_function(self) -> None:
        import services.gateway.teaching_pack_export_writer as mod

        assert not hasattr(mod, "_gift_payload")

    def test_no_h5p_payload_function(self) -> None:
        import services.gateway.teaching_pack_export_writer as mod

        assert not hasattr(mod, "_h5p_payload")

    def test_no_qti_payload_function(self) -> None:
        import services.gateway.teaching_pack_export_writer as mod

        assert not hasattr(mod, "_qti_payload")

    def test_no_assessment_payload_function(self) -> None:
        import services.gateway.teaching_pack_export_writer as mod

        assert not hasattr(mod, "_assessment_payload")

    def test_no_assessment_formats_function(self) -> None:
        import services.gateway.teaching_pack_export_writer as mod

        assert not hasattr(mod, "_assessment_formats")
