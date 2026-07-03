from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUB_AGENTS_ROOT = PROJECT_ROOT / "packages" / "agents" / "sub_agents"


def test_sub_agents_do_not_bypass_agent_runtime() -> None:
    offenders: list[str] = []
    for path in SUB_AGENTS_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "complete_json_chat" in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []
