from __future__ import annotations

from typing import Any


def with_strategy_lineage(slot: dict[str, Any], component: dict[str, Any]) -> dict[str, Any]:
    parent_slot_id = slot.get("parent_slot_id")
    result = {
        **component,
        "strategy_slot_id": str(slot.get("slot_id", "")),
        "strategy_learning_move_id": str(slot.get("learning_move_id", "")),
        "strategy_objective_refs": [*_dicts(slot.get("objective_refs"))],
    }
    if isinstance(parent_slot_id, str) and parent_slot_id:
        result["strategy_parent_slot_id"] = parent_slot_id
    return result


def _dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
