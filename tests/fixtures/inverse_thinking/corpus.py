from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

FixtureKind = Literal["positive", "negative"]
JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class CorpusCase:
    case_id: str
    kind: FixtureKind
    path: Path
    sha256: str
    data: JsonObject


def inverse_thinking_fixture_root() -> Path:
    return Path(__file__).resolve().parent


def load_all_fixtures() -> list[CorpusCase]:
    root = inverse_thinking_fixture_root()
    manifest = _read_json(root / "manifest.json")
    return [_load_case(root, entry) for entry in manifest["fixtures"]]


def load_positive_fixtures() -> list[CorpusCase]:
    return [case for case in load_all_fixtures() if case.kind == "positive"]


def load_negative_fixtures() -> list[CorpusCase]:
    return [case for case in load_all_fixtures() if case.kind == "negative"]


def load_fixture(case_id: str) -> CorpusCase:
    for fixture in load_all_fixtures():
        if fixture.case_id == case_id:
            return fixture
    msg = f"Unknown inverse-thinking fixture: {case_id}"
    raise KeyError(msg)


def fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_case(root: Path, entry: JsonObject) -> CorpusCase:
    path = root / str(entry["path"])
    data = _read_json(path)
    return CorpusCase(
        case_id=str(entry["case_id"]),
        kind=_fixture_kind(str(entry["kind"])),
        path=path,
        sha256=str(entry["sha256"]),
        data=data,
    )


def _fixture_kind(value: str) -> FixtureKind:
    match value:
        case "positive" | "negative":
            return value
        case _:
            msg = f"Unsupported inverse-thinking fixture kind: {value}"
            raise ValueError(msg)


def _read_json(path: Path) -> JsonObject:
    return json.loads(path.read_text(encoding="utf-8"))
