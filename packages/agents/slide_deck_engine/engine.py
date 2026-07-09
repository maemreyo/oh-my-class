from __future__ import annotations

from packages.agents.slide_deck_engine.deck_shape import annotate_pedagogical_pacing
from packages.agents.slide_deck_engine.models import (
    SlideDeckEngineRequest,
    SlideDeckEngineResult,
    SlideDeckTraceMetadata,
)
from packages.agents.slide_deck_engine.phases.content_materialization import materialize_deck
from packages.agents.slide_deck_engine.phases.density_accessibility_audit import audit_density_and_accessibility
from packages.agents.slide_deck_engine.phases.export_readiness import check_export_readiness
from packages.agents.slide_deck_engine.phases.input_assembly import assemble_input
from packages.agents.slide_deck_engine.phases.interaction_planning import plan_interactions
from packages.agents.slide_deck_engine.phases.layout_composition import compose_layouts
from packages.agents.slide_deck_engine.phases.pedagogical_planning import plan_pedagogy
from packages.agents.slide_deck_engine.phases.slide_architecture import plan_slide_architecture
from packages.agents.slide_deck_engine.phases.surface_readiness import check_surface_readiness
from packages.agents.slide_deck_engine.quality import (
    build_healing_reports,
    build_scorecard,
    trace_artifacts,
    validate_media_support,
    validate_objective_coverage,
    validate_pacing,
    validate_registry_membership,
    validate_source_references,
    validate_teacher_only_separation,
)
from packages.agents.slide_deck_engine.scoped_regeneration import apply_scoped_feedback, feedback_target_from_request


class SlideDeckEngine:
    async def generate(self, request: SlideDeckEngineRequest) -> SlideDeckEngineResult:
        assembled = assemble_input(request)
        pedagogy = plan_pedagogy(assembled)
        architecture = plan_slide_architecture(assembled)
        compose_layouts(architecture)
        plan_interactions()
        deck, llm_calls = await materialize_deck(assembled, pedagogy)
        deck, scoped_repair = apply_scoped_feedback(deck, feedback_target_from_request(request))
        deck = annotate_pedagogical_pacing(deck, assembled.effective_teacher_constraints)
        validations = [
            *validate_registry_membership(deck),
            *audit_density_and_accessibility(deck, assembled.effective_teacher_constraints, assembled.grade_level),
            validate_pacing(deck),
            validate_source_references(deck),
            validate_objective_coverage(deck, pedagogy),
            validate_media_support(deck),
            validate_teacher_only_separation(deck),
            check_surface_readiness(deck),
            check_export_readiness(deck),
        ]
        healing_reports = build_healing_reports(validations)
        scorecard = build_scorecard(validations, deck)
        (
            plan_artifact,
            data_artifact,
            validation_artifact,
            healing_artifact,
            scorecard_artifact,
            source_ref_map,
            model_cost_metadata,
            export_readiness_manifest,
            scoped_regeneration_artifact,
        ) = trace_artifacts(deck, architecture, validations, healing_reports, scorecard, scoped_repair, llm_calls=llm_calls)
        return SlideDeckEngineResult(
            deck=deck,
            validation_reports=validations,
            healing_reports=healing_reports,
            scorecard=scorecard,
            trace=SlideDeckTraceMetadata(
                run_id=request.run_id,
                phases=[
                    "input_assembly",
                    "pedagogical_planning",
                    "slide_architecture_planning",
                    "layout_composition",
                    "interaction_planning",
                    "content_materialization",
                    "density_accessibility_audit",
                    "surface_readiness",
                    "export_readiness",
                ],
                llm_calls=llm_calls,
                plan_artifact=plan_artifact,
                data_artifact=data_artifact,
                validation_artifact=validation_artifact,
                healing_artifact=healing_artifact,
                scorecard_artifact=scorecard_artifact,
                source_ref_map=source_ref_map,
                model_cost_metadata=model_cost_metadata,
                export_readiness_manifest=export_readiness_manifest,
                scoped_regeneration_artifact=scoped_regeneration_artifact,
            ),
        )
