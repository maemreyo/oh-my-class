"""#473: privacy-preserving effectiveness and item-quality feedback contracts."""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Literal

from pydantic import Field, model_validator

from common.contracts.pedagogical_compiler.common import FrozenContract, stable_id

EventKind = Literal[
    "response", "omission", "completion", "teacher_edit", "teacher_rejection", "export_usage", "live_usage",
]
SignalStatus = Literal["insufficient_sample", "observed"]


class EffectivenessEvent(FrozenContract):
    event_id: str
    tenant_id: str
    pseudonymous_actor_id: str | None = None
    document_id: str
    document_version: int = Field(ge=1)
    item_id: str | None = None
    answer_set_version: int | None = Field(default=None, ge=1)
    event_kind: EventKind
    correct: bool | None = None
    omitted: bool = False
    distractor_id: str | None = None
    timing_band: Literal["fast", "typical", "slow", "unknown"] = "unknown"
    retention_tier: Literal["ephemeral", "operational", "analytics"] = "analytics"
    opted_out: bool = False

    @model_validator(mode="after")
    def _lineage_complete(self) -> "EffectivenessEvent":
        if self.item_id is not None and self.answer_set_version is None and self.event_kind in {"response", "omission"}:
            raise ValueError("item response events require exact answer_set_version")
        return self


class ItemObservation(FrozenContract):
    observation_id: str
    tenant_id: str
    document_id: str
    document_version: int
    item_id: str
    answer_set_version: int
    sample_size: int
    status: SignalStatus
    difficulty: float | None = Field(default=None, ge=0.0, le=1.0)
    omission_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    distractor_functioning: dict[str, float] = Field(default_factory=dict)
    timing_distribution: dict[str, int] = Field(default_factory=dict)
    uncertainty_note: str


class TeacherRevisionOutcome(FrozenContract):
    outcome_id: str
    tenant_id: str
    document_id: str
    before_version: int
    after_version: int
    item_id: str | None = None
    edit_types: tuple[str, ...]
    revision_severity: Literal["minor", "material", "rejected"]
    policy_mutated: bool = False


class AggregateQualitySignal(FrozenContract):
    signal_id: str
    tenant_id: str
    document_id: str
    document_version: int
    item_id: str
    answer_set_version: int
    status: SignalStatus
    sample_size: int
    metrics: dict[str, float]
    uncertainty_note: str
    causal_claim: Literal[False] = False


class PolicyProposal(FrozenContract):
    proposal_id: str
    source_signal_ids: tuple[str, ...]
    proposed_change: str
    review_required: Literal[True] = True
    automatically_applied: Literal[False] = False


def pseudonymize_actor(tenant_id: str, actor_id: str, *, salt: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}|{salt}|{actor_id}".encode("utf-8")).hexdigest()
    return f"actor-{digest[:24]}"


def aggregate_item_observations(
    events: tuple[EffectivenessEvent, ...],
    *,
    minimum_sample: int = 10,
) -> tuple[ItemObservation, ...]:
    groups: dict[tuple[str, str, int, str, int], list[EffectivenessEvent]] = defaultdict(list)
    for event in events:
        if event.opted_out or event.item_id is None or event.answer_set_version is None:
            continue
        if event.event_kind not in {"response", "omission"}:
            continue
        key = (event.tenant_id, event.document_id, event.document_version, event.item_id, event.answer_set_version)
        groups[key].append(event)
    observations: list[ItemObservation] = []
    for key in sorted(groups):
        tenant_id, document_id, document_version, item_id, answer_version = key
        group = groups[key]
        sample_size = len(group)
        if sample_size < minimum_sample:
            observations.append(ItemObservation(
                observation_id=stable_id("item-observation", key, sample_size),
                tenant_id=tenant_id, document_id=document_id, document_version=document_version,
                item_id=item_id, answer_set_version=answer_version, sample_size=sample_size,
                status="insufficient_sample", uncertainty_note=f"withheld below minimum sample {minimum_sample}",
            ))
            continue
        answered = [event for event in group if not event.omitted and event.correct is not None]
        correct_count = sum(bool(event.correct) for event in answered)
        distractor_counts: dict[str, int] = defaultdict(int)
        timing: dict[str, int] = defaultdict(int)
        for event in group:
            if event.distractor_id:
                distractor_counts[event.distractor_id] += 1
            timing[event.timing_band] += 1
        observations.append(ItemObservation(
            observation_id=stable_id("item-observation", key, sample_size),
            tenant_id=tenant_id, document_id=document_id, document_version=document_version,
            item_id=item_id, answer_set_version=answer_version, sample_size=sample_size,
            status="observed",
            difficulty=round(correct_count / max(1, len(answered)), 4),
            omission_rate=round(sum(event.omitted for event in group) / sample_size, 4),
            distractor_functioning={name: round(count / sample_size, 4) for name, count in sorted(distractor_counts.items())},
            timing_distribution=dict(sorted(timing.items())),
            uncertainty_note="observed behavior only; no causal learning claim",
        ))
    return tuple(observations)


def signals_from_observations(observations: tuple[ItemObservation, ...]) -> tuple[AggregateQualitySignal, ...]:
    return tuple(
        AggregateQualitySignal(
            signal_id=stable_id("quality-signal", observation.observation_id),
            tenant_id=observation.tenant_id,
            document_id=observation.document_id,
            document_version=observation.document_version,
            item_id=observation.item_id,
            answer_set_version=observation.answer_set_version,
            status=observation.status,
            sample_size=observation.sample_size,
            metrics={
                key: value for key, value in {
                    "difficulty": observation.difficulty,
                    "omission_rate": observation.omission_rate,
                }.items() if value is not None
            },
            uncertainty_note=observation.uncertainty_note,
        )
        for observation in observations
    )


def propose_policy_review(signals: tuple[AggregateQualitySignal, ...], *, change: str) -> PolicyProposal:
    observed = tuple(signal.signal_id for signal in signals if signal.status == "observed")
    if not observed:
        raise ValueError("policy proposals require at least one observed signal above the privacy threshold")
    return PolicyProposal(
        proposal_id=stable_id("policy-proposal", observed, change),
        source_signal_ids=observed,
        proposed_change=change,
    )
