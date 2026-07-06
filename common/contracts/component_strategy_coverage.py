from __future__ import annotations

from common.contracts.component_strategy import (
    ComponentStrategyRequest,
    ObjectiveCoverage,
    ObjectiveRef,
    StrategyVariant,
)


def slot_objective_refs(request: ComponentStrategyRequest) -> tuple[ObjectiveRef, ...]:
    refs = tuple(ref for ref in request.objective_refs if ref.assessable and ref.importance != "extension")
    return refs or request.objective_refs


def coverage_for(request: ComponentStrategyRequest, variant: StrategyVariant) -> tuple[ObjectiveCoverage, ...]:
    covered_by_objective = {
        ref.objective_id: tuple(
            slot.slot_id
            for slot in variant.learning_sequence
            if any(slot_ref.objective_id == ref.objective_id for slot_ref in slot.objective_refs)
        )
        for ref in request.objective_refs
    }
    coverage: list[ObjectiveCoverage] = []
    for ref in request.objective_refs:
        slot_ids = covered_by_objective[ref.objective_id]
        if ref.importance == "extension":
            coverage.append(ObjectiveCoverage(
                objective_ref=ref,
                coverage_state="deferred",
                note="Extension objective deferred with visible non-blocking note.",
            ))
        elif slot_ids and ref.assessable:
            coverage.append(ObjectiveCoverage(
                objective_ref=ref,
                coverage_state="covered",
                slot_ids=slot_ids,
                note="Objective has pack-level strategy coverage.",
            ))
        else:
            coverage.append(ObjectiveCoverage(
                objective_ref=ref,
                coverage_state="uncovered",
                note="Core/supporting objective has no pack-level coverage.",
            ))
    return tuple(coverage)
