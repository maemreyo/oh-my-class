"""Application service for privacy-safe effectiveness ingestion (#473)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from common.contracts.effectiveness.feedback import EffectivenessEvent, pseudonymize_actor
from common.contracts.effectiveness.governance import EffectivenessLedger


@dataclass(frozen=True)
class ResponseIngestion:
    event_id: str
    tenant_id: str
    actor_id: str
    document_id: str
    document_version: int
    item_id: str
    answer_set_version: int
    correct: bool | None
    omitted: bool = False
    distractor_id: str | None = None
    timing_band: Literal["fast", "typical", "slow", "unknown"] = "unknown"
    source: Literal["live_session", "export"] = "live_session"
    opted_out: bool = False


class EffectivenessIngestionService:
    def __init__(self, ledger: EffectivenessLedger, *, pseudonym_salt: str) -> None:
        if not pseudonym_salt:
            raise ValueError("pseudonym salt is required")
        self._ledger = ledger
        self._salt = pseudonym_salt

    def ingest(self, request: ResponseIngestion) -> bool:
        actor = pseudonymize_actor(request.tenant_id, request.actor_id, salt=self._salt)
        event = EffectivenessEvent(
            event_id=request.event_id,
            tenant_id=request.tenant_id,
            pseudonymous_actor_id=actor,
            document_id=request.document_id,
            document_version=request.document_version,
            item_id=request.item_id,
            answer_set_version=request.answer_set_version,
            event_kind="omission" if request.omitted else "response",
            correct=request.correct,
            omitted=request.omitted,
            distractor_id=request.distractor_id,
            timing_band=request.timing_band,
            opted_out=request.opted_out,
        )
        return self._ledger.append(event)
