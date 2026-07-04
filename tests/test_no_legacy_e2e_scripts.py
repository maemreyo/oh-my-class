from __future__ import annotations

import re
from pathlib import Path

# Legacy /run API was decommissioned (HTTP 410) per ADR-018.
# All new code must use /teaching-packs/runs instead.
_LEGACY_RUN_CREATE = re.compile(r'"POST"\s*,\s*"/run"')
_LEGACY_RUN_APPROVE = re.compile(r'"/run/[^"]*?/approve"')


def test_legacy_run_e2e_scripts_are_retired() -> None:
    assert not Path("scripts/test_full_flow.py").exists()
    assert not Path("scripts/test_e2e_real_llm.py").exists()
    assert "run_teacher_scenarios.py" in Path("scripts/run_e2e.sh").read_text(encoding="utf-8")


def test_no_script_calls_decommissioned_run_api() -> None:
    """No script may POST to the legacy /run create or /run/{id}/approve endpoints (HTTP 410)."""
    scripts_dir = Path("scripts")
    violations: list[str] = []
    for py_file in sorted(scripts_dir.glob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        if _LEGACY_RUN_CREATE.search(source):
            violations.append(f"{py_file}: calls legacy POST /run (create)")
        if _LEGACY_RUN_APPROVE.search(source):
            violations.append(f"{py_file}: calls legacy /run/{{id}}/approve")
    assert not violations, "Found scripts calling the decommissioned /run API:\n" + "\n".join(violations)
