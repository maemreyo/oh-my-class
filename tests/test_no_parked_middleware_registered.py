from __future__ import annotations

from pathlib import Path

from packages.agents.middleware import ORDERED_MIDDLEWARE_LIST


ROOT = Path(__file__).resolve().parents[1]
PARKED_MIDDLEWARE_NAMES = frozenset({
    "dangling_tool_call",
    "tool_error_handling",
    "loop_detection",
    "subagent_limit",
    "deferred_tool_filter",
    "summarization",
    "todo_list",
    "view_image",
})


def test_no_parked_react_registry_exists() -> None:
    source = (ROOT / "packages/agents/middleware/registry.py").read_text(encoding="utf-8")

    assert "PARKED_REACT_MIDDLEWARE" not in source


def test_no_parked_middleware_is_registered() -> None:
    active_names = {middleware.name for middleware in ORDERED_MIDDLEWARE_LIST}

    assert active_names.isdisjoint(PARKED_MIDDLEWARE_NAMES)


def test_active_middleware_order_is_contiguous_with_clarification_last() -> None:
    orders = [middleware.order for middleware in ORDERED_MIDDLEWARE_LIST]

    assert orders == list(range(1, len(ORDERED_MIDDLEWARE_LIST) + 1))
    assert ORDERED_MIDDLEWARE_LIST[-1].name == "clarification"
