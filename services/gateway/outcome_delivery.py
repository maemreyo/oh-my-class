from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

from common.contracts.outcome import DeliveryRecord
from sqlalchemy.exc import SQLAlchemyError

from services.gateway.outcome_store import record_delivery
from services.gateway.teaching_pack_types import JsonObject, JsonValue, RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class OutcomeDeliverySink(Protocol):
    async def record_post_export_delivery(
        self,
        run_id: RunId,
        teacher_id: str,
        state: JsonObject,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class OutcomeDeliveryWriteError(Exception):
    run_id: RunId

    def __str__(self) -> str:
        return f"outcome delivery write failed for run {self.run_id}"


@dataclass(frozen=True, slots=True)
class SqlAlchemyOutcomeDeliverySink:
    session_factory: async_sessionmaker[AsyncSession]

    async def record_post_export_delivery(
        self,
        run_id: RunId,
        teacher_id: str,
        state: JsonObject,
    ) -> None:
        contract = _json_object(state.get("contract"))
        record = DeliveryRecord(
            delivery_id=f"delivery-{uuid4()}",
            run_id=run_id,
            teacher_id=teacher_id,
            kc_ids=delivered_kc_ids(state),
            delivered_at=datetime.now(UTC),
            class_id=_optional_string(contract.get("class_id")),
        )
        try:
            async with self.session_factory() as session:
                await record_delivery(session, record)
                await session.commit()
        except SQLAlchemyError as exc:
            raise OutcomeDeliveryWriteError(run_id) from exc


def delivered_kc_ids(state: JsonObject) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in _delivery_sources(state):
        _collect_kc_ids(value, seen, ordered)
    return ordered


def _delivery_sources(state: JsonObject) -> list[JsonValue]:
    return [
        state.get("contract"),
        state.get("artifacts"),
        state.get("rendered_snapshots"),
    ]


def _collect_kc_ids(value: JsonValue, seen: set[str], ordered: list[str]) -> None:
    match value:
        case dict():
            kc_values = value.get("kc_ids")
            if isinstance(kc_values, list):
                for item in kc_values:
                    if isinstance(item, str) and item not in seen:
                        seen.add(item)
                        ordered.append(item)
            for child in value.values():
                _collect_kc_ids(child, seen, ordered)
        case list():
            for child in value:
                _collect_kc_ids(child, seen, ordered)
        case str() | int() | float() | bool() | None:
            return


def _json_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _optional_string(value: JsonValue | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
