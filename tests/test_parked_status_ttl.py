from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[1]
MAX_PARKED_DAYS: Final = 90
PARKED_STATUS_PATTERN: Final = re.compile(r"(?im)^Status:\s*Parked\s*$")
PARKED_UNTIL_PATTERN: Final = re.compile(r"(?im)^Parked-Until:\s*(\d{4}-\d{2}-\d{2})\s*$")
SCAN_ROOTS: Final = (
    ROOT / "packages",
    ROOT / "services",
    ROOT / "common",
    ROOT / "apps",
    ROOT / "skills",
    ROOT / "scripts",
    ROOT / "infra",
    ROOT / "docs/adr",
    ROOT / "docs/system",
)
IGNORED_PARTS: Final = frozenset({".git", ".scratch", "node_modules", "__pycache__"})


@dataclass(frozen=True, slots=True)
class ParkedViolation:
    path: Path
    reason: str


def _text_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    ]


def _parked_violations(paths: list[Path], *, today: date) -> list[ParkedViolation]:
    violations: list[ParkedViolation] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PARKED_STATUS_PATTERN.search(source) is None:
            continue
        match = PARKED_UNTIL_PATTERN.search(source)
        if match is None:
            violations.append(ParkedViolation(path=path, reason="missing Parked-Until"))
            continue
        parked_until = date.fromisoformat(match.group(1))
        if parked_until < today:
            violations.append(ParkedViolation(path=path, reason=f"expired on {parked_until.isoformat()}"))
            continue
        parked_days = (parked_until - today).days
        if parked_days > MAX_PARKED_DAYS:
            violations.append(ParkedViolation(path=path, reason=f"expires in {parked_days} days"))
    return violations


def test_live_parked_components_have_unexpired_ttl() -> None:
    paths = [path for root in SCAN_ROOTS if root.exists() for path in _text_files(root)]
    violations = _parked_violations(paths, today=date.today())

    assert violations == []


def test_expired_fixture_proves_ttl_policy_detects_expiry() -> None:
    fixture = ROOT / "tests/fixtures/parked_status_ttl/expired_component.md"
    violations = _parked_violations([fixture], today=date(2026, 7, 3))

    assert violations == [ParkedViolation(path=fixture, reason="expired on 2000-01-01")]


def test_missing_date_fixture_proves_ttl_policy_requires_expiry() -> None:
    fixture = ROOT / "tests/fixtures/parked_status_ttl/missing_date_component.md"
    violations = _parked_violations([fixture], today=date(2026, 7, 3))

    assert violations == [ParkedViolation(path=fixture, reason="missing Parked-Until")]
