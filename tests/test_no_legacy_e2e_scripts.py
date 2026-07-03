from __future__ import annotations

from pathlib import Path


def test_legacy_run_e2e_scripts_are_retired() -> None:
    assert not Path("scripts/test_full_flow.py").exists()
    assert not Path("scripts/test_e2e_real_llm.py").exists()
    assert "run_teacher_scenarios.py" in Path("scripts/run_e2e.sh").read_text(encoding="utf-8")
