from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from services.gateway.pipeline_v2_control_store import GateInterruptCreate, PipelineV2ControlStore
from services.gateway.pipeline_v2_models import PipelineV2EventVisibility
from services.gateway.pipeline_v2_store import PipelineV2EventCreate, PipelineV2RunStore

if TYPE_CHECKING:
    from services.gateway.pipeline_v2_types import JsonObject, RunId
    from services.gateway.research_engine import SearchPlan


@dataclass(frozen=True, slots=True)
class SearchPlanGateOpened:
    gate_id: str


@dataclass(frozen=True, slots=True)
class SearchPlanGateSkipped:
    reason: str


type SearchPlanGateResult = SearchPlanGateOpened | SearchPlanGateSkipped


async def prepare_search_plan_gate(
    *,
    run_id: RunId,
    plan: SearchPlan,
    control_store: PipelineV2ControlStore,
    run_store: PipelineV2RunStore,
) -> SearchPlanGateResult:
    if not plan.requires_confirmation:
        await run_store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.search_plan.skipped_confirmation",
            visibility=PipelineV2EventVisibility.INTERNAL,
            payload={"query_count": plan.brief.query_count},
        ))
        return SearchPlanGateSkipped(reason="not_required")

    gate_id = f"gate-{uuid4()}"
    await control_store.open_gate(GateInterruptCreate(
        gate_id=gate_id,
        run_id=run_id,
        gate_name="search_plan_confirmation",
        payload=_gate_payload(gate_id, plan),
    ))
    await run_store.write_event(PipelineV2EventCreate(
        run_id=run_id,
        event_name="pipeline_v2.search_plan_confirmation.opened",
        visibility=PipelineV2EventVisibility.TEACHER,
        payload={"gate_id": gate_id, "query_count": plan.brief.query_count},
    ))
    return SearchPlanGateOpened(gate_id=gate_id)


def _gate_payload(gate_id: str, plan: SearchPlan) -> JsonObject:
    return {
        "gate_id": gate_id,
        "gate_name": "search_plan_confirmation",
        "confirmation_reasons": list(plan.confirmation_reasons),
        "queries": [{"query": query.query, "purpose": query.purpose} for query in plan.queries],
        "brief": plan.brief.model_dump(mode="json"),
    }
