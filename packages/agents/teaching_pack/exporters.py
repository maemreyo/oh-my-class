from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, assert_never

type ExportFormat = Literal["html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "pptx"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

_SUPPORTED_FORMATS = frozenset({"html", "gift", "h5p", "qti", "anki_apkg", "flashcard_tsv", "pptx"})
_PUBLISH_TARGETS = frozenset({"google_forms"})


class UnsupportedExportFormatError(RuntimeError):
    def __init__(self, export_format: str) -> None:
        self.export_format = export_format
        super().__init__(f"Unsupported export format: {export_format}")


@dataclass(frozen=True, slots=True)
class ExportRequest:
    run_id: str
    format: ExportFormat
    snapshots: list[JsonObject]
    contract: JsonObject


class ExporterRegistry:
    @classmethod
    def default(cls) -> ExporterRegistry:
        return cls()

    def supports(self, export_format: str) -> bool:
        return export_format in _SUPPORTED_FORMATS

    def is_explicitly_unsupported(self, export_format: str) -> bool:
        return export_format in _PUBLISH_TARGETS

    def export(self, request: ExportRequest) -> list[str]:
        match request.format:
            case "html":
                return _html_exports(request.run_id, request.snapshots)
            case "gift":
                return [f"exports/{request.run_id}/{request.run_id}.gift.txt"]
            case "h5p":
                return [f"exports/{request.run_id}/{request.run_id}.h5p"]
            case "qti":
                return [f"exports/{request.run_id}/{request.run_id}.qti.xml"]
            case "anki_apkg":
                return [f"exports/{request.run_id}/{request.run_id}.apkg"]
            case "flashcard_tsv":
                return [f"exports/{request.run_id}/{request.run_id}.tsv"]
            case "pptx":
                return _pptx_exports(request.run_id, request.snapshots)
            case unreachable:
                assert_never(unreachable)


def requested_export_formats(contract: JsonObject) -> list[ExportFormat]:
    values = contract.get("export_formats")
    if not isinstance(values, list) or not values:
        return ["html"]
    formats: list[ExportFormat] = []
    for value in values:
        export_format = _export_format(str(value))
        formats.append(export_format)
    if "html" not in formats:
        return ["html", *formats]
    return formats


def _export_format(value: str) -> ExportFormat:
    match value:
        case "html":
            return "html"
        case "gift":
            return "gift"
        case "h5p":
            return "h5p"
        case "qti":
            return "qti"
        case "anki_apkg":
            return "anki_apkg"
        case "flashcard_tsv":
            return "flashcard_tsv"
        case "pptx":
            return "pptx"
        case _:
            raise UnsupportedExportFormatError(value)


def _html_exports(run_id: str, snapshots: list[JsonObject]) -> list[str]:
    return [f"exports/{run_id}/{snapshot_id}.html" for snapshot_id in _snapshot_ids(snapshots)]


def _pptx_exports(run_id: str, snapshots: list[JsonObject]) -> list[str]:
    # pptx conversion only makes sense for slide_deck content (SDX-05) —
    # unlike html, this does not fan out over every snapshot regardless of type.
    slide_deck_ids = [
        str(snapshot["snapshot_id"])
        for snapshot in snapshots
        if snapshot.get("artifact_type") == "slide_deck"
    ]
    return [f"exports/{run_id}/{snapshot_id}.pptx" for snapshot_id in slide_deck_ids]


def _snapshot_ids(snapshots: list[JsonObject]) -> list[str]:
    return [str(snapshot["snapshot_id"]) for snapshot in snapshots]
