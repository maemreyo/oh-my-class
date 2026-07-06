import type { TeachingPackEventPayload } from "@/hooks/use-teaching-packs";

export function strategyBlueprintEvent(): TeachingPackEventPayload {
	return {
		blueprint: {
			topic: "Phân số",
			grade_level: "Grade 5",
			subject: "Math",
			duration_minutes: 45,
			learning_objectives: [{ objective: "So sánh hai phân số", bloom_level: "understand" }],
		},
		component_strategy_plan: {
			strategy_id: "strategy-fractions",
			strategy_schema_version: "component_strategy.v1",
			knowledge_db_version: "knowledge.v1",
			selector_version: "selector.v1",
			scoring_profile_id: "default",
			blueprint_revision_id: "bp-1",
			objective_refs: [{ objective_id: "LO-1", objective_revision: "rev-1" }],
			rationale_text: "Use contrastive examples before independent practice so students can see why denominators matter.",
			rationale_facts: ["Prior knowledge is mixed", "Worksheet export supports the selected components"],
			recommended: strategyVariant("recommended", "Contrastive fractions", "concept_math", 0.91, null),
			variants: [
				strategyVariant("variant-practice", "Practice-first fractions", "practice_first", 0.78, null),
				strategyVariant("variant-fallback", "Fallback drill", "fallback_drill", 0.66, {
					fallback_graph_version: "fallback.v1",
					original_component_type: "interactive_number_line",
					fallback_component_type: "question_list",
					reason_code: "export_unsupported",
					teacher_visible_note: "Interactive number line is replaced with a printable question list for HTML export.",
				}),
			],
		},
	};
}

function strategyVariant(
	variantId: string,
	displayLabel: string,
	strategyFamilyId: string,
	overall: number,
	fallbackMetadata: Readonly<Record<string, unknown>> | null,
): Readonly<Record<string, unknown>> {
	return {
		variant_id: variantId,
		strategy_family_id: strategyFamilyId,
		display_label: displayLabel,
		learning_sequence: [
			{
				slot_id: `${variantId}-slot-1`,
				sequence_id: "seq-1",
				phase: "concept_building",
				learning_move_id: "contrastive_pairs",
				component_type: "vocab_cluster",
				component_binding_id: "binding-1",
				objective_refs: [{ objective_id: "LO-1", objective_revision: "rev-1" }],
				target_artifacts: ["lesson", "worksheet"],
				budget: {
					ideal_time_minutes: 10,
					max_time_minutes: 15,
					ideal_item_count: 4,
					max_item_count: 6,
					teacher_load_level: "medium",
				},
			},
		],
		artifact_strategies: [{ artifact_type: "worksheet", ordered_slot_ids: [`${variantId}-slot-1`], notes_for_creator: ["Keep answer explanations teacher-only"] }],
		export_projection_status: [{ export_format: "html", slot_id: `${variantId}-slot-1`, state: "supported", reason: "Printable output remains self-contained" }],
		quality_score: { overall, objective_alignment: overall, evidence_signal_coverage: overall, component_diversity: overall, compliance_safety: "pass" },
		fallback_metadata: fallbackMetadata,
	};
}
