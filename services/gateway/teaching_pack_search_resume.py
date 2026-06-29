from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from common.contracts.run_contract import RunContract
from services.gateway.notifications import notify_search_confirmation
from services.gateway.research_engine import plan_search
from services.gateway.research_gate import SearchPlanGateOpened, prepare_search_plan_gate
from services.gateway.teaching_pack_control_store import TeachingPackControlStore
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId


@dataclass(frozen=True, slots=True)
class SearchPlanResumeContext:
    run_id: RunId
    teacher_id: TeacherId
    session: AsyncSession
    control_store: TeachingPackControlStore


async def open_search_plan_gate_if_required(
    context: SearchPlanResumeContext,
    contract_json: dict[str, object],
) -> bool:
    search_gate = await prepare_search_plan_gate(
        run_id=context.run_id,
        plan=plan_search(RunContract.model_validate(contract_json)),
        control_store=context.control_store,
        run_store=TeachingPackRunStore(context.session),
    )
    if not isinstance(search_gate, SearchPlanGateOpened):
        return False

    await notify_search_confirmation(context.run_id, context.teacher_id, context.session)
    return True
