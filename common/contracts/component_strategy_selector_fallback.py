from __future__ import annotations

from dataclasses import dataclass

from common.contracts.component_strategy import (
    ComponentStrategyRequest,
    FallbackMetadata,
    StrategyRevision,
    StrategyWarning,
)
from common.contracts.component_strategy_knowledge_models import ComponentBindingEntry, FallbackPolicyEntry
from common.contracts.component_strategy_selector_support import preference_values


@dataclass(frozen=True, slots=True)
class FallbackSelection:
    bindings: tuple[ComponentBindingEntry, ...]
    metadata: FallbackMetadata | None
    warnings: tuple[StrategyWarning, ...]


def apply_component_rejections(
    request: ComponentStrategyRequest,
    bindings: tuple[ComponentBindingEntry, ...],
    policies: tuple[FallbackPolicyEntry, ...],
) -> FallbackSelection:
    rejected_components = preference_values(request, "reject_component_family")
    if not rejected_components:
        return FallbackSelection(bindings=bindings, metadata=None, warnings=())
    fallback_by_component = {policy.from_component_type: policy for policy in policies}
    selected: list[ComponentBindingEntry] = []
    fallback_metadata: FallbackMetadata | None = None
    warnings: tuple[StrategyWarning, ...] = ()
    for binding in bindings:
        if binding.component_type not in rejected_components:
            selected.append(binding)
            continue
        if not has_explicit_component_feedback(request, binding.component_type):
            selected.append(binding)
            warnings = (*warnings, relaxed_warning(f"component preference {binding.component_type}"))
            continue
        policy = fallback_by_component[binding.component_type]
        selected.append(
            binding.model_copy(
                update={
                    "binding_id": f"{binding.binding_id}.fallback.{policy.policy_id}",
                    "component_type": policy.to_component_type,
                    "fallback_policy_id": policy.policy_id,
                }
            )
        )
        fallback_metadata = metadata_from(policy, binding.component_type)
    return FallbackSelection(bindings=tuple(selected), metadata=fallback_metadata, warnings=warnings)


def has_explicit_feedback(request: ComponentStrategyRequest, event_type: str) -> bool:
    if request.teacher_preferences is None:
        return False
    return any(
        event.event_type == event_type and event.source == "teacher"
        for event in request.teacher_preferences.feedback_events
    )


def relaxed_warning(preference: str) -> StrategyWarning:
    return StrategyWarning(
        code="fallback_used",
        message=f"Relaxed implicit {preference} because it would remove every valid strategy path.",
    )


def revision_for(fallback_metadata: FallbackMetadata | None) -> StrategyRevision:
    if fallback_metadata is None:
        return StrategyRevision(
            revision_id="rev-1",
            parent_revision_id=None,
            actor="system",
            reason="initial deterministic selection",
            materiality="none",
            teacher_reapproval_required=False,
        )
    return StrategyRevision(
        revision_id="rev-1",
        parent_revision_id=None,
        actor="system",
        reason=f"fallback applied: {fallback_metadata.reason_code}",
        materiality="teacher_visible",
        teacher_reapproval_required=True,
    )


def has_explicit_component_feedback(request: ComponentStrategyRequest, component_type: str) -> bool:
    if request.teacher_preferences is None:
        return False
    return any(
        event.event_type == "reject_component_family"
        and event.source == "teacher"
        and event.value == component_type
        for event in request.teacher_preferences.feedback_events
    )


def metadata_from(policy: FallbackPolicyEntry, original_component_type: str) -> FallbackMetadata:
    return FallbackMetadata(
        fallback_graph_version="fallback_graph.v1",
        original_component_type=original_component_type,
        fallback_component_type=policy.to_component_type,
        reason_code=policy.reason_code,
        teacher_visible_note=policy.teacher_message,
        severity=policy.severity,
        fallback_quality=policy.fallback_quality,
        preserved_affordances=policy.preserved_affordances,
        lost_affordances=policy.lost_affordances,
    )
