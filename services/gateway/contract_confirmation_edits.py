from __future__ import annotations

from pydantic import ValidationError

from common.contracts.run_contract import DecompositionIntent


def contract_confirmation_edits(response: dict[str, object]) -> dict[str, object]:
    edits: dict[str, object] = {}
    mode = response.get("mode")
    if mode in {"generate_pack", "plan_unit", "diagnose_then_generate"}:
        edits["mode"] = mode
    decomposition_intent = response.get("decomposition_intent")
    if isinstance(decomposition_intent, dict):
        try:
            intent = DecompositionIntent.model_validate(decomposition_intent)
        except ValidationError:
            return edits
        edits["decomposition_intent"] = intent.model_dump()
    return edits
