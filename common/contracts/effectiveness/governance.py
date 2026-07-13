"""Privacy ledger, diagnostics, and policy boundary for #473."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from common.contracts.effectiveness.feedback import (
    AggregateQualitySignal,
    EffectivenessEvent,
    ItemObservation,
    aggregate_item_observations,
    signals_from_observations,
)


@dataclass(frozen=True)
class ItemDiagnostic:
    tenant_id: str
    document_id: str
    document_version: int
    item_id: str
    answer_set_version: int
    sample_size: int
    difficulty: float | None
    discrimination: float | None
    reliability: float | None
    ambiguity_alert: bool
    uncertainty_note: str


class PrivacyViolation(ValueError):
    pass


class EffectivenessLedger:
    def __init__(self) -> None:
        self._events: list[EffectivenessEvent] = []
        self._opted_out: set[tuple[str, str]] = set()
        self._deleted: set[tuple[str, str]] = set()

    def opt_out(self, tenant_id: str, pseudonymous_actor_id: str) -> None:
        self._opted_out.add((tenant_id, pseudonymous_actor_id))
        self.delete_actor(tenant_id, pseudonymous_actor_id)

    def delete_actor(self, tenant_id: str, pseudonymous_actor_id: str) -> int:
        key = (tenant_id, pseudonymous_actor_id)
        before = len(self._events)
        self._events = [
            event for event in self._events
            if (event.tenant_id, event.pseudonymous_actor_id) != key
        ]
        self._deleted.add(key)
        return before - len(self._events)

    def append(self, event: EffectivenessEvent) -> bool:
        actor = event.pseudonymous_actor_id
        if actor is not None and not actor.startswith("actor-"):
            raise PrivacyViolation("actor identifiers must be pseudonymized before ingestion")
        key = (event.tenant_id, actor or "")
        if event.opted_out or key in self._opted_out or key in self._deleted:
            return False
        self._events.append(event)
        return True

    def events_for_tenant(self, tenant_id: str) -> tuple[EffectivenessEvent, ...]:
        return tuple(event for event in self._events if event.tenant_id == tenant_id)


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    return None if denominator == 0 else round(numerator / denominator, 4)


def build_item_diagnostics(
    events: Iterable[EffectivenessEvent],
    *,
    minimum_sample: int = 10,
) -> tuple[ItemDiagnostic, ...]:
    event_tuple = tuple(events)
    observations = aggregate_item_observations(event_tuple, minimum_sample=minimum_sample)
    actor_scores: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for event in event_tuple:
        if (
            event.event_kind == "response"
            and event.pseudonymous_actor_id
            and event.item_id
            and event.correct is not None
            and not event.opted_out
        ):
            actor_scores[(event.tenant_id, event.pseudonymous_actor_id)][event.item_id] = float(event.correct)
    diagnostics: list[ItemDiagnostic] = []
    for observation in observations:
        discrimination: float | None = None
        if observation.status == "observed":
            xs: list[float] = []
            ys: list[float] = []
            for (tenant_id, _actor), scores in actor_scores.items():
                if tenant_id != observation.tenant_id or observation.item_id not in scores or len(scores) < 2:
                    continue
                xs.append(scores[observation.item_id])
                ys.append(sum(value for item, value in scores.items() if item != observation.item_id) / (len(scores) - 1))
            discrimination = _correlation(xs, ys)
        distractor_peak = max(observation.distractor_functioning.values(), default=0.0)
        ambiguity = observation.status == "observed" and (
            (observation.omission_rate or 0.0) >= 0.25 or distractor_peak >= 0.45 or (discrimination is not None and discrimination < 0.0)
        )
        diagnostics.append(ItemDiagnostic(
            tenant_id=observation.tenant_id,
            document_id=observation.document_id,
            document_version=observation.document_version,
            item_id=observation.item_id,
            answer_set_version=observation.answer_set_version,
            sample_size=observation.sample_size,
            difficulty=observation.difficulty,
            discrimination=discrimination,
            reliability=None,
            ambiguity_alert=ambiguity,
            uncertainty_note=observation.uncertainty_note,
        ))
    return tuple(diagnostics)


def governed_signals(
    ledger: EffectivenessLedger,
    tenant_id: str,
    *,
    minimum_sample: int = 10,
) -> tuple[AggregateQualitySignal, ...]:
    observations: tuple[ItemObservation, ...] = aggregate_item_observations(
        ledger.events_for_tenant(tenant_id), minimum_sample=minimum_sample
    )
    return signals_from_observations(observations)
