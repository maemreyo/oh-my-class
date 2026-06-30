"""Doc-presence test: each failure-mode runbook exists and has the required sections."""
from __future__ import annotations

from pathlib import Path

import pytest

RUNBOOKS_DIR = Path(__file__).parent.parent / "docs" / "runbooks"

FAILURE_MODES = [
    "provider-down",
    "job-queue-stuck",
    "gate-timeout",
    "render-pool-crash",
    "db-restore",
    "content-recall",
]

REQUIRED_SECTIONS = [
    "## Symptom",
    "## Alert",
    "## Diagnosis",
    "## Remediation",
    "## Escalation",
    "## Verify",
]


@pytest.mark.parametrize("mode", FAILURE_MODES)
def test_runbook_file_exists(mode: str) -> None:
    path = RUNBOOKS_DIR / f"{mode}.md"
    assert path.exists(), f"Runbook not found: {path}"


@pytest.mark.parametrize("mode", FAILURE_MODES)
def test_runbook_has_required_sections(mode: str) -> None:
    path = RUNBOOKS_DIR / f"{mode}.md"
    assert path.exists(), f"Runbook not found: {path}"
    content = path.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in content, (
            f"Runbook '{mode}.md' is missing section '{section}'"
        )
