"""Tests for anki_apkg / flashcard_tsv export wiring — deterministic, no LLM."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from packages.agents.teaching_pack.exporters import (
    ExportRequest,
    ExporterRegistry,
    UnsupportedExportFormatError,
    requested_export_formats,
)


# ── ExporterRegistry ─────────────────────────────────────────────────────────


def test_supports_anki_apkg() -> None:
    assert ExporterRegistry.default().supports("anki_apkg") is True


def test_supports_flashcard_tsv() -> None:
    assert ExporterRegistry.default().supports("flashcard_tsv") is True


def test_google_forms_still_unsupported() -> None:
    registry = ExporterRegistry.default()
    assert registry.supports("google_forms") is False
    assert registry.is_explicitly_unsupported("google_forms") is True


def test_export_anki_returns_apkg_path() -> None:
    registry = ExporterRegistry.default()
    paths = registry.export(ExportRequest(
        run_id="run-abc",
        format="anki_apkg",
        snapshots=[],
        contract={},
    ))
    assert paths == ["exports/run-abc/run-abc.apkg"]


def test_export_tsv_returns_tsv_path() -> None:
    registry = ExporterRegistry.default()
    paths = registry.export(ExportRequest(
        run_id="run-xyz",
        format="flashcard_tsv",
        snapshots=[],
        contract={},
    ))
    assert paths == ["exports/run-xyz/run-xyz.tsv"]


def test_requested_export_formats_includes_anki() -> None:
    contract = {"export_formats": ["html", "anki_apkg"]}
    formats = requested_export_formats(contract)
    assert "anki_apkg" in formats
    assert "html" in formats


def test_requested_export_formats_unknown_raises() -> None:
    with pytest.raises(UnsupportedExportFormatError):
        requested_export_formats({"export_formats": ["unknown_format"]})


# ── Export writer — subprocess routing ───────────────────────────────────────


def test_subprocess_formats_extracted() -> None:
    from services.gateway.teaching_pack_export_writer import _subprocess_formats

    state = {
        "contract": {"export_formats": ["html", "anki_apkg", "flashcard_tsv", "gift"]},
    }
    formats = _subprocess_formats(state)
    assert set(formats) == {"anki_apkg", "flashcard_tsv", "gift"}


def test_gift_h5p_qti_routed_to_subprocess() -> None:
    from services.gateway.teaching_pack_export_writer import _subprocess_formats

    state = {
        "contract": {"export_formats": ["html", "anki_apkg", "flashcard_tsv", "gift", "h5p", "qti"]},
    }
    formats = _subprocess_formats(state)
    assert set(formats) == {"anki_apkg", "flashcard_tsv", "gift", "h5p", "qti"}


# ── Fail-closed: CLI not built ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_export_fails_closed_when_cli_missing(tmp_path: Path) -> None:
    from services.gateway.teaching_pack_export_writer import ExportAdapterError, _node_export

    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", tmp_path / "nonexistent.js"):
        with pytest.raises(ExportAdapterError, match="Export CLI not built"):
            await _node_export("anki_apkg", "run-1", [], tmp_path)


@pytest.mark.asyncio
async def test_node_export_fails_closed_on_nonzero_exit(tmp_path: Path) -> None:
    from services.gateway.teaching_pack_export_writer import ExportAdapterError, _node_export

    fake_cli = tmp_path / "cli.js"
    fake_cli.write_text("process.exit(1)")

    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", fake_cli):
        with pytest.raises(ExportAdapterError, match="exited 1"):
            await _node_export("anki_apkg", "run-1", [], tmp_path)


@pytest.mark.asyncio
async def test_node_export_fails_closed_on_cli_error_field(tmp_path: Path) -> None:
    from services.gateway.teaching_pack_export_writer import ExportAdapterError, _node_export

    fake_cli = tmp_path / "cli.js"
    fake_cli.write_text('process.stdout.write(JSON.stringify({error:"bad deck"}))')

    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", fake_cli):
        with pytest.raises(ExportAdapterError, match="bad deck"):
            await _node_export("anki_apkg", "run-1", [], tmp_path)


@pytest.mark.asyncio
async def test_node_export_returns_path_on_success(tmp_path: Path) -> None:
    from services.gateway.teaching_pack_export_writer import _node_export

    out_file = tmp_path / "run-1.apkg"
    out_file.write_bytes(b"")
    fake_cli = tmp_path / "cli.js"
    fake_cli.write_text(f'process.stdout.write(JSON.stringify({{path:"{out_file}"}}));')

    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", fake_cli):
        result = await _node_export("anki_apkg", "run-1", [], tmp_path)
    assert result == str(out_file)


# ── Manifest sync ─────────────────────────────────────────────────────────────


def test_manifest_export_formats_includes_anki_and_tsv() -> None:
    manifest_path = Path("docs/system/architecture.manifest.json")
    if not manifest_path.exists():
        pytest.skip("architecture.manifest.json not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    supported = manifest["export_formats"]["supported"]
    assert "anki_apkg" in supported, f"anki_apkg missing from manifest supported: {supported}"
    assert "flashcard_tsv" in supported, f"flashcard_tsv missing from manifest supported: {supported}"
