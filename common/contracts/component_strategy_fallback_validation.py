from __future__ import annotations

from collections.abc import Callable

from common.contracts.component_strategy_knowledge_models import ComponentBindingEntry, FallbackPolicyEntry

RequireComponent = Callable[[str], None]


class FallbackKnowledgeValidationError(ValueError):
    pass


def validate_fallback_graph(
    bindings: tuple[ComponentBindingEntry, ...],
    policies: tuple[FallbackPolicyEntry, ...],
    require_component: RequireComponent,
) -> None:
    for policy in policies:
        _require_fallback_policy(policy, require_component)
    _require_acyclic_fallbacks(policies)
    _require_required_binding_fallbacks(bindings, policies)


def _require_fallback_policy(policy: FallbackPolicyEntry, require_component: RequireComponent) -> None:
    require_component(policy.from_component_type)
    if policy.fallback_policy != "no_fallback_allowed":
        require_component(policy.to_component_type)
    if policy.fallback_policy == "no_fallback_allowed" and (
        not policy.reason_code or not policy.severity or not policy.teacher_options
    ):
        raise FallbackKnowledgeValidationError(
            f"no-fallback policy {policy.policy_id} needs reason, severity, and options"
        )


def _require_acyclic_fallbacks(policies: tuple[FallbackPolicyEntry, ...]) -> None:
    graph = {policy.from_component_type: policy.to_component_type for policy in policies}
    for start in graph:
        seen: set[str] = set()
        current = start
        while current in graph:
            if current in seen:
                raise FallbackKnowledgeValidationError(f"circular fallback path at {start}")
            seen.add(current)
            current = graph[current]


def _require_required_binding_fallbacks(
    bindings: tuple[ComponentBindingEntry, ...],
    policies: tuple[FallbackPolicyEntry, ...],
) -> None:
    policies_by_id = {policy.policy_id: policy for policy in policies}
    fallback_sources = {policy.from_component_type for policy in policies if policy.fallback_policy == "required"}
    for binding in bindings:
        policy = policies_by_id[binding.fallback_policy_id]
        if policy.fallback_policy == "required" and binding.component_type not in fallback_sources:
            raise FallbackKnowledgeValidationError(f"missing required fallback for {binding.binding_id}")
