from __future__ import annotations

from common.contracts.component_strategy import (
    ArtifactStrategyProjection,
    ComponentStrategyPlan,
    ComponentStrategyRequest,
    ComponentStrategyResult,
    ExportProjectionStatus,
    FallbackMetadata,
    StrategyBlockingIssue,
    StrategySlot,
    StrategyVariant,
    StrategyWarning,
)
from common.contracts.component_strategy_knowledge import (
    DEFAULT_KNOWLEDGE_SOURCE_PATH,
    load_knowledge_source,
    validate_knowledge_source,
)
from common.contracts.component_strategy_knowledge_models import ComponentBindingEntry
from common.contracts.component_strategy_coverage import coverage_for, slot_objective_refs
from common.contracts.component_strategy_slot_policy import (
    artifact_scope_recommendations_for,
    delivery_context_for,
    fill_requirements_for,
    forbidden_fill_patterns,
    scaffold_slot_for,
    scoring_intent_for,
    slot_budget_for,
    teacher_load_multiplier,
)
from common.contracts.component_strategy_selector_fallback import (
    apply_component_rejections,
    has_explicit_feedback,
    relaxed_warning,
    revision_for,
)
from common.contracts.component_strategy_selector_support import (
    family_id_for,
    grade_band_for,
    phase_for,
    preference_values,
    quality_for,
    score_binding,
    subject_tag_for,
)

SELECTOR_VERSION = "selector.v1"
STRATEGY_SCHEMA_VERSION = "component_strategy.v1"


def plan_component_strategy(request: ComponentStrategyRequest) -> ComponentStrategyResult:
    family_id = family_id_for(request)
    rejected_families = preference_values(request, "reject_component_family")
    if family_id in rejected_families:
        return _blocked(
            "feedback_conflict",
            request,
            f"Teacher feedback rejects required strategy family {family_id}.",
            ("keep_recommended_strategy", "revise_learning_goal", "choose_different_pack_scope"),
        )
    if request.mode == "provisional":
        return ComponentStrategyResult(
            status="planned",
            plan=None,
            hypotheses=(f"{family_id} is likely to fit this pack.",),
            research_questions=(
                "Which misconceptions or prior-knowledge gaps should shape component choice?",
                "Which evidence signals raise or lower factual and prerequisite risk?",
            ),
        )

    if request.research_signals is not None and str(request.research_signals.prerequisite_risk) == "missing_blocking":
        return _blocked(
            "prerequisite_missing",
            request,
            "Prerequisite readiness is missing and blocks this strategy.",
            ("add_prerequisite_pack", "revise_objective_scope", "switch_to_diagnostic"),
        )

    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    report = validate_knowledge_source(source)
    candidates = _eligible_bindings(request, family_id, report.production_bindings)
    rejected_moves = preference_values(request, "reject_learning_move")
    warnings: tuple[StrategyWarning, ...] = ()
    if rejected_moves:
        filtered = tuple(binding for binding in candidates if binding.learning_move_id not in rejected_moves)
        if filtered:
            candidates = filtered
        elif has_explicit_feedback(request, "reject_learning_move"):
            return _blocked(
                "feedback_conflict",
                request,
                "Teacher feedback rejects every valid learning move for this strategy.",
                ("allow_one_required_move", "revise_objective", "change_artifact_scope"),
            )
        else:
            warnings = (relaxed_warning("learning-move preference"),)
    if not candidates:
        return _blocked("no_eligible_component", request, "No eligible component binding remains.")

    ranked = sorted(candidates, key=lambda binding: (-score_binding(binding, request), binding.binding_id))
    selected = _diverse_prefix(ranked)
    fallback = apply_component_rejections(request, selected, source.fallback_policies)
    selected = fallback.bindings
    warnings = (*warnings, *fallback.warnings)
    variant = _variant_for(request, family_id, selected, fallback.metadata)
    if request.research_signals is not None and str(request.research_signals.prerequisite_risk) == "missing_scaffoldable":
        variant = variant.model_copy(update={"learning_sequence": (scaffold_slot_for(request, variant.learning_sequence[0]), *variant.learning_sequence)})
    coverage = coverage_for(request, variant)
    uncovered_core = tuple(item for item in coverage if item.coverage_state == "uncovered" and item.objective_ref.importance == "core")
    if uncovered_core:
        return _blocked(
            "core_objective_uncovered",
            request,
            "One or more core objectives have no pack-level strategy coverage.",
            ("add_targeted_component", "revise_objective_scope", "defer_to_follow_up_pack"),
            affected_objective_ids=tuple(item.objective_ref.objective_id for item in uncovered_core),
        )
    deferred_extension = tuple(item for item in coverage if item.coverage_state == "deferred")
    if deferred_extension:
        warnings = (*warnings, StrategyWarning(
            code="objective_deferred",
            message="Extension objective deferred from the core pack strategy.",
            slot_ids=(),
        ))
    status = "planned_with_fallback" if fallback.metadata is not None else "planned"
    revision = revision_for(fallback.metadata)
    plan = ComponentStrategyPlan(
        strategy_id=f"strategy-{request.run_id}-rev-1",
        strategy_schema_version=STRATEGY_SCHEMA_VERSION,
        knowledge_db_version=source.manifest.knowledge_db_version,
        selector_version=SELECTOR_VERSION,
        scoring_profile_id="evidence_balanced_default",
        blueprint_revision_id=str(request.delivery_context.get("blueprint_revision_id", "bp-rev-1")),
        objective_refs=request.objective_refs,
        recommended=variant,
        variants=(),
        rationale_text=f"Selected {family_id} using deterministic hard filters and score signals.",
        rationale_facts=(
            f"{len(selected)} component binding(s) passed artifact, subject, grade, duration, and safety filters.",
        ),
        audit_score_ledger={**variant.quality_score.audit_ledger, "teacher_load_multiplier": teacher_load_multiplier(request)},
        objective_coverage=coverage,
        delivery_context=delivery_context_for(request),
        artifact_scope_recommendations=artifact_scope_recommendations_for(request),
        revision=revision,
    )
    return ComponentStrategyResult(status=status, plan=plan, warnings=warnings)


def _eligible_bindings(
    request: ComponentStrategyRequest,
    family_id: str,
    bindings: tuple[ComponentBindingEntry, ...],
) -> tuple[ComponentBindingEntry, ...]:
    grade_band = grade_band_for(request.grade_level)
    subject_tag = subject_tag_for(request)
    return tuple(
        binding
        for binding in bindings
        if family_id in binding.strategy_family_ids
        and any(artifact in binding.artifact_types for artifact in request.artifact_types)
        and subject_tag in binding.subject_tags
        and grade_band in binding.grade_bands
        and binding.duration_min_minutes <= request.duration_minutes
        and binding.compliance_risk != "high"
    )


def _variant_for(
    request: ComponentStrategyRequest,
    family_id: str,
    bindings: tuple[ComponentBindingEntry, ...],
    fallback_metadata: FallbackMetadata | None = None,
) -> StrategyVariant:
    slots = tuple(_slot_for(request, binding, index) for index, binding in enumerate(bindings, start=1))
    artifact_strategies = tuple(
        ArtifactStrategyProjection(
            artifact_type=artifact_type,
            ordered_slot_ids=tuple(slot.slot_id for slot in slots if artifact_type in slot.target_artifacts),
        )
        for artifact_type in request.artifact_types
        if any(artifact_type in slot.target_artifacts for slot in slots)
    )
    export_status = tuple(
        ExportProjectionStatus(export_format=export_format, slot_id=slot.slot_id, state="ready")
        for export_format in request.export_formats
        for slot in slots
    )
    return StrategyVariant(
        variant_id="recommended",
        strategy_family_id=family_id,
        display_label="Recommended",
        learning_sequence=slots,
        artifact_strategies=artifact_strategies,
        export_projection_status=export_status,
        quality_score=quality_for(bindings, request),
        fallback_metadata=fallback_metadata,
    )


def _slot_for(
    request: ComponentStrategyRequest,
    binding: ComponentBindingEntry,
    index: int,
) -> StrategySlot:
    slot_minutes = max(1, min(binding.duration_max_minutes, request.duration_minutes // max(1, index + 1)))
    objective_refs = slot_objective_refs(request)
    return StrategySlot(
        slot_id=f"{request.run_id}/{binding.component_type}/slot-{index}",
        sequence_id=f"seq-{index}",
        phase=phase_for(binding),
        learning_move_id=binding.learning_move_id,
        component_type=binding.component_type,
        component_binding_id=binding.binding_id,
        objective_refs=objective_refs,
        target_artifacts=tuple(artifact for artifact in request.artifact_types if artifact in binding.artifact_types),
        required_affordances=binding.udl_tags,
        fill_requirements=fill_requirements_for(binding.learning_move_id),
        forbidden_fill_patterns=forbidden_fill_patterns(),
        accessibility_intent=binding.udl_tags,
        differentiation_intent=binding.bloom_levels,
        budget=slot_budget_for(request, min_minutes=binding.duration_min_minutes, max_minutes=slot_minutes),
        scoring_intent=scoring_intent_for(request),
    )


def _diverse_prefix(bindings: list[ComponentBindingEntry]) -> tuple[ComponentBindingEntry, ...]:
    selected: list[ComponentBindingEntry] = []
    seen_components: set[str] = set()
    for binding in bindings:
        if binding.component_type in seen_components:
            continue
        selected.append(binding)
        seen_components.add(binding.component_type)
        if len(selected) == 3:
            break
    return tuple(selected or bindings[:1])


def _blocked(
    code: str,
    request: ComponentStrategyRequest,
    message: str,
    teacher_options: tuple[str, ...] = (),
    affected_objective_ids: tuple[str, ...] | None = None,
) -> ComponentStrategyResult:
    return ComponentStrategyResult(
        status="blocked",
        plan=None,
        blocking_issues=(
            StrategyBlockingIssue(
                code=code,
                message=message,
                affected_objective_ids=affected_objective_ids or tuple(ref.objective_id for ref in request.objective_refs),
                teacher_options=teacher_options,
            ),
        ),
    )
