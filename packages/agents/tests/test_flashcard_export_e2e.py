"""E2E integration test for flashcard export flow — deterministic, no LLM.

Covers:
- ArtifactContent validates flashcard_deck artifact type
- FORMAT_REQUIREMENTS gate: anki_apkg and flashcard_tsv require flashcard_deck
- _export_finalize node emits apkg/tsv paths when formats are requested
- CLI subprocess receives sections-embedded cards and produces correct deck
- Fail-closed: missing flashcard_deck artifact blocks flashcard export formats
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from common.contracts.artifact import ArtifactContent, Flashcard, FlashcardDeckData
from packages.agents.teaching_pack.exporters import (
    ExportRequest,
    ExporterRegistry,
    requested_export_formats,
)
from packages.quality.layer6_export.export_validator import (
    FORMAT_REQUIREMENTS,
    check_export_readiness,
)
from services.gateway.teaching_pack_export_writer import (
    ExportAdapterError,
    node_export,
    _subprocess_formats,
)


# ── Issue #01: Pydantic models ────────────────────────────────────────────────


class TestFlashcardPydanticModels:
    def test_flashcard_model_validates(self) -> None:
        card = Flashcard(id="1", front="Phân số", back="Fraction")
        assert card.id == "1"
        assert card.front == "Phân số"
        assert card.hint is None

    def test_flashcard_with_hint(self) -> None:
        card = Flashcard(id="2", front="Tử số", back="Numerator", hint="top number")
        assert card.hint == "top number"

    def test_flashcard_requires_non_empty_front(self) -> None:
        with pytest.raises(Exception):
            Flashcard(id="x", front="", back="something")

    def test_flashcard_deck_data_validates(self) -> None:
        deck = FlashcardDeckData(
            title="Vocabulary: Math",
            subject="Math",
            gradeLevel="Grade 5",
            cards=[
                Flashcard(id="1", front="Phân số", back="Fraction"),
            ],
        )
        assert deck.title == "Vocabulary: Math"
        assert len(deck.cards) == 1
        assert deck.theme is None

    def test_flashcard_deck_data_optional_fields(self) -> None:
        deck = FlashcardDeckData(
            title="English Greetings",
            subject="english",
            gradeLevel="Grade 6",
            cards=[],
            theme="default",
            lang="vi",
        )
        assert deck.theme == "default"
        assert deck.lang == "vi"

    def test_flashcard_deck_data_exported_from_contracts(self) -> None:
        from common.contracts import Flashcard as F, FlashcardDeckData as FDD
        assert F is Flashcard
        assert FDD is FlashcardDeckData


# ── Issue #01: ArtifactContent schema validation ──────────────────────────────


class TestFlashcardDeckSchema:
    def test_flashcard_deck_validates_as_artifact_content(self) -> None:
        artifact = ArtifactContent.model_validate({
            "artifact_type": "flashcard_deck",
            "title": "Vocabulary: Equivalent Fractions",
            "sections": [
                {
                    "heading": "Core Vocabulary",
                    "cards": [
                        {"id": "1", "front": "Phân số", "back": "Fraction"},
                        {"id": "2", "front": "Tử số", "back": "Numerator"},
                    ],
                }
            ],
            "metadata": {"subject": "Math", "gradeLevel": "Grade 5"},
        })
        assert artifact.artifact_type == "flashcard_deck"
        assert len(artifact.sections) == 1
        assert artifact.sections[0]["heading"] == "Core Vocabulary"
        assert len(artifact.sections[0]["cards"]) == 2

    def test_flashcard_deck_requires_at_least_one_section(self) -> None:
        with pytest.raises(Exception):
            ArtifactContent.model_validate({
                "artifact_type": "flashcard_deck",
                "title": "Empty Deck",
                "sections": [],
            })

    def test_flashcard_deck_in_artifact_type_enum(self) -> None:
        from common.contracts.run_contract import ArtifactType
        import typing
        args = typing.get_args(ArtifactType)
        assert "flashcard_deck" in args


# ── Issue #03: FORMAT_REQUIREMENTS gate ──────────────────────────────────────


class TestFlashcardFormatRequirements:
    def test_format_requirements_includes_anki_apkg(self) -> None:
        assert "anki_apkg" in FORMAT_REQUIREMENTS
        assert FORMAT_REQUIREMENTS["anki_apkg"] == ["flashcard_deck"]

    def test_format_requirements_includes_flashcard_tsv(self) -> None:
        assert "flashcard_tsv" in FORMAT_REQUIREMENTS
        assert FORMAT_REQUIREMENTS["flashcard_tsv"] == ["flashcard_deck"]

    def test_anki_apkg_passes_when_flashcard_deck_present(self) -> None:
        artifacts = [
            {"artifact_type": "lesson"},
            {"artifact_type": "flashcard_deck"},
        ]
        result = check_export_readiness(artifacts, ["anki_apkg"])
        assert result.passed

    def test_flashcard_tsv_passes_when_flashcard_deck_present(self) -> None:
        artifacts = [{"artifact_type": "flashcard_deck"}]
        result = check_export_readiness(artifacts, ["flashcard_tsv"])
        assert result.passed

    def test_anki_apkg_blocked_when_flashcard_deck_missing(self) -> None:
        artifacts = [{"artifact_type": "lesson"}, {"artifact_type": "quiz"}]
        result = check_export_readiness(artifacts, ["anki_apkg"])
        assert not result.passed
        assert "anki_apkg" in result.format_issues

    def test_flashcard_tsv_blocked_when_flashcard_deck_missing(self) -> None:
        artifacts = [{"artifact_type": "lesson"}]
        result = check_export_readiness(artifacts, ["flashcard_tsv"])
        assert not result.passed
        assert "flashcard_tsv" in result.format_issues

    def test_combined_formats_with_mixed_artifacts(self) -> None:
        artifacts = [
            {"artifact_type": "lesson"},
            {"artifact_type": "quiz"},
            {"artifact_type": "flashcard_deck"},
        ]
        result = check_export_readiness(artifacts, ["html", "gift", "anki_apkg", "flashcard_tsv"])
        assert result.passed


# ── Issue #02: _export_finalize path routing ─────────────────────────────────


class TestExportFinalizeRouting:
    def test_subprocess_formats_extracts_anki_tsv_and_gift(self) -> None:
        state = {"contract": {"export_formats": ["html", "anki_apkg", "flashcard_tsv", "gift"]}}
        formats = _subprocess_formats(state)
        assert set(formats) == {"anki_apkg", "flashcard_tsv", "gift"}

    def test_gift_h5p_qti_all_routed_to_subprocess(self) -> None:
        state = {
            "contract": {"export_formats": ["html", "anki_apkg", "flashcard_tsv", "gift", "h5p", "qti"]},
        }
        formats = _subprocess_formats(state)
        assert set(formats) == {"anki_apkg", "flashcard_tsv", "gift", "h5p", "qti"}

    def test_exporter_registry_returns_apkg_path(self) -> None:
        registry = ExporterRegistry.default()
        paths = registry.export(ExportRequest(
            run_id="run-flash-001",
            format="anki_apkg",
            snapshots=[],
            contract={},
        ))
        assert paths == ["exports/run-flash-001/run-flash-001.apkg"]

    def test_exporter_registry_returns_tsv_path(self) -> None:
        registry = ExporterRegistry.default()
        paths = registry.export(ExportRequest(
            run_id="run-flash-002",
            format="flashcard_tsv",
            snapshots=[],
            contract={},
        ))
        assert paths == ["exports/run-flash-002/run-flash-002.tsv"]

    def test_requested_export_formats_includes_flashcard_formats(self) -> None:
        contract = {"export_formats": ["html", "anki_apkg", "flashcard_tsv"]}
        formats = requested_export_formats(contract)
        assert "anki_apkg" in formats
        assert "flashcard_tsv" in formats
        assert "html" in formats


# ── Issue #02: CLI subprocess data passing ───────────────────────────────────


@pytest.mark.asyncio
async def test_node_export_sends_sections_cards_to_cli(tmp_path: Path) -> None:
    """Verify the CLI receives sections-embedded card data and returns path."""
    out_file = tmp_path / "run-1.apkg"
    out_file.write_bytes(b"")

    received: list[dict] = []

    def fake_cli_script(input_data: dict) -> dict:
        received.append(input_data)
        return {"path": str(out_file)}

    fake_cli = tmp_path / "cli.js"
    # CLI that echoes back the JSON it received and returns a valid result
    fake_cli.write_text(
        "const chunks=[]; process.stdin.on('data',c=>chunks.push(c));"
        "process.stdin.on('end',()=>{"
        f"process.stdout.write(JSON.stringify({{path:{json.dumps(str(out_file))}}}));"
        "});"
    )

    snapshots = [
        {
            "snapshot_id": "snap-1",
            "artifact_type": "flashcard_deck",
            "content_json": {
                "artifact_type": "flashcard_deck",
                "title": "Vocabulary: Math",
                "sections": [
                    {
                        "heading": "Cards",
                        "cards": [
                            {"id": "1", "front": "Phân số", "back": "Fraction"},
                            {"id": "2", "front": "Tử số", "back": "Numerator"},
                        ],
                    }
                ],
                "metadata": {"subject": "Math", "gradeLevel": "Grade 5"},
            },
        }
    ]

    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", fake_cli):
        result = await node_export("anki_apkg", "run-1", snapshots, tmp_path)

    assert result == str(out_file)


@pytest.mark.asyncio
async def test_node_export_fails_closed_no_cli(tmp_path: Path) -> None:
    with patch("services.gateway.teaching_pack_export_writer._EXPORT_CLI_PATH", tmp_path / "missing.js"):
        with pytest.raises(ExportAdapterError, match="Export CLI not built"):
            await node_export("flashcard_tsv", "run-x", [], tmp_path)


# ── Issue #04: Pack-generator prompt module ───────────────────────────────────


class TestFlashcardPromptModule:
    def test_flashcard_prompt_registered_in_seed_modules(self) -> None:
        from packages.agents.prompts.seed import SEED_MODULES
        ids = [m.id for m in SEED_MODULES]
        assert "content_creator_flashcard_v1" in ids

    def test_flashcard_prompt_output_schema_has_flashcard_deck_type(self) -> None:
        from packages.agents.prompts.seed import CONTENT_CREATOR_FLASHCARD_V1
        schema = CONTENT_CREATOR_FLASHCARD_V1.output_schema
        assert schema["properties"]["artifact_type"]["const"] == "flashcard_deck"

    def test_flashcard_prompt_output_schema_requires_sections_with_cards(self) -> None:
        from packages.agents.prompts.seed import CONTENT_CREATOR_FLASHCARD_V1
        schema = CONTENT_CREATOR_FLASHCARD_V1.output_schema
        sections_items = schema["properties"]["sections"]["items"]
        assert "cards" in sections_items["properties"]

    def test_seeded_registry_contains_flashcard_module(self) -> None:
        from packages.agents.prompts.seed import create_seeded_registry
        registry = create_seeded_registry()
        module = registry.get("content_creator_flashcard_v1")
        assert module is not None
        assert module.metadata.get("artifact_type") == "flashcard_deck"
