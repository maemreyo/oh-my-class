/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ComponentStrategyPlanSchema = z.object({ "strategy_id": z.string().min(1).max(120), "strategy_schema_version": z.string().min(1).max(80), "knowledge_db_version": z.string().min(1).max(80), "selector_version": z.string().min(1).max(80), "scoring_profile_id": z.string().min(1).max(120), "blueprint_revision_id": z.string().min(1).max(80), "objective_refs": z.array(z.lazy(() => ObjectiveRefSchema)).min(1), "recommended": z.lazy(() => StrategyVariantSchema), "variants": z.array(z.lazy(() => StrategyVariantSchema)).optional(), "rationale_text": z.string().min(1).max(1200), "rationale_facts": z.array(z.string()).optional(), "audit_score_ledger": z.record(z.string(), z.union([z.number(), z.string(), z.boolean()])).optional(), "objective_coverage": z.array(z.any()).optional(), "delivery_context": z.any().optional(), "artifact_scope_recommendations": z.array(z.any()).optional(), "revision": z.union([z.lazy(() => StrategyRevisionSchema), z.null()]).default(null) })


export const StrategyVariantSchema = z.object({ "variant_id": z.string().min(1).max(80), "strategy_family_id": z.string().min(1).max(120), "display_label": z.string().min(1).max(120), "learning_sequence": z.array(z.lazy(() => StrategySlotSchema)).min(1), "artifact_strategies": z.array(z.lazy(() => ArtifactStrategyProjectionSchema)).min(1), "export_projection_status": z.array(z.lazy(() => ExportProjectionStatusSchema)).optional(), "quality_score": z.lazy(() => StrategyQualityScoreSchema), "fallback_metadata": z.union([z.lazy(() => FallbackMetadataSchema), z.null()]).default(null), "rejection_reasons": z.array(z.string()).optional() })


export const StrategySlotSchema = z.object({ "slot_id": z.string().min(1).max(160), "sequence_id": z.string().min(1).max(120), "phase": z.string().min(1).max(80), "learning_move_id": z.string().min(1).max(120), "component_type": z.string().min(1).max(120), "component_binding_id": z.string().min(1).max(160), "objective_refs": z.array(z.lazy(() => ObjectiveRefSchema)).min(1), "target_artifacts": z.array(z.string()).min(1), "required_affordances": z.array(z.string()).optional(), "fill_requirements": z.array(z.string()).optional(), "forbidden_fill_patterns": z.array(z.string()).optional(), "accessibility_intent": z.array(z.string()).optional(), "differentiation_intent": z.array(z.string()).optional(), "budget": z.lazy(() => StrategySlotBudgetSchema), "scoring_intent": z.any().optional(), "teacher_action_intent": z.array(z.string()).optional(), "student_instruction_constraints": z.array(z.string()).optional(), "misconception_targets": z.array(z.any()).optional(), "expansion_policy": z.any().optional(), "parent_slot_id": z.union([z.string().max(160), z.null()]).default(null) })


export const StrategySlotBudgetSchema = z.object({ "ideal_time_minutes": z.number().int().gte(1).lte(180), "max_time_minutes": z.number().int().gte(1).lte(180), "ideal_item_count": z.number().int().gte(1).lte(100), "max_item_count": z.number().int().gte(1).lte(100), "teacher_load_level": z.enum(["low","medium","high"]).default("medium"), "reading_level": z.string().min(1).max(80).default("grade_level"), "cognitive_load": z.any().default("medium"), "scaffold_level": z.any().default("low"), "print_density": z.any().default("medium"), "grading_load": z.any().default("low") })


export const ArtifactStrategyProjectionSchema = z.object({ "artifact_type": z.string().min(1).max(80), "ordered_slot_ids": z.array(z.string()).min(1), "notes_for_creator": z.array(z.string()).optional() })


export const ExportProjectionStatusSchema = z.object({ "export_format": z.string().min(1).max(80), "slot_id": z.string().min(1).max(160), "state": z.any(), "fallback_component_type": z.union([z.string().max(120), z.null()]).default(null), "reason": z.union([z.string().max(500), z.null()]).default(null) })


export const FallbackMetadataSchema = z.object({ "fallback_graph_version": z.string().min(1).max(80), "original_component_type": z.string().min(1).max(120), "fallback_component_type": z.string().min(1).max(120), "reason_code": z.string().min(1).max(120), "teacher_visible_note": z.string().min(1).max(500), "severity": z.enum(["info","warning","block"]).default("warning"), "fallback_quality": z.number().gte(0).lte(1).default(1), "preserved_affordances": z.array(z.string()).optional(), "lost_affordances": z.array(z.string()).optional() })


export const StrategyQualityScoreSchema = z.object({ "overall": z.number().gte(0).lte(1), "objective_alignment": z.number().gte(0).lte(1), "evidence_signal_coverage": z.number().gte(0).lte(1), "component_diversity": z.number().gte(0).lte(1), "compliance_safety": z.any(), "audit_ledger": z.record(z.string(), z.union([z.number(), z.string(), z.boolean()])).optional() })


export const StrategyBlockingIssueSchema = z.object({ "code": z.any(), "message": z.string().min(1).max(500), "affected_objective_ids": z.array(z.string()).optional(), "teacher_options": z.array(z.string()).optional() })


export const StrategyWarningSchema = z.object({ "code": z.any(), "message": z.string().min(1).max(500), "slot_ids": z.array(z.string()).optional() })


export const StrategyRevisionSchema = z.object({ "revision_id": z.string().min(1).max(80), "parent_revision_id": z.union([z.string().max(80), z.null()]).default(null), "actor": z.any(), "reason": z.string().min(1).max(500), "materiality": z.any().default("none"), "teacher_reapproval_required": z.boolean() })


export const ObjectiveRefSchema = z.object({ "objective_id": z.string().min(1).max(80), "objective_revision": z.string().min(1).max(80), "importance": z.enum(["core","supporting","extension"]).default("core"), "assessable": z.boolean().default(true) })


export const ComponentStrategyResultSchema = z.object({ "status": z.any(), "plan": z.union([z.lazy(() => ComponentStrategyPlanSchema), z.null()]).default(null), "research_questions": z.array(z.string()).optional(), "hypotheses": z.array(z.string()).optional(), "blocking_issues": z.array(z.union([z.any(), z.any()])).optional(), "warnings": z.array(z.lazy(() => StrategyWarningSchema)).optional() })




export const ComponentStrategyRequestSchema = z.object({ "mode": z.any(), "run_id": z.string().min(1).max(80), "teacher_id_hash": z.string().min(1).max(128), "locale": z.string().min(2).max(16), "subject": z.string().min(1).max(80), "grade_level": z.string().min(1).max(80), "duration_minutes": z.number().int().gte(10).lte(180), "artifact_types": z.array(z.string()).min(1), "export_formats": z.array(z.string()).min(1), "objective_refs": z.array(z.object({ "objective_id": z.string().min(1).max(80), "objective_revision": z.string().min(1).max(80), "importance": z.enum(["core","supporting","extension"]).default("core"), "assessable": z.boolean().default(true) })).min(1), "delivery_context": z.record(z.string(), z.union([z.string(), z.number().int(), z.boolean()])).optional(), "delivery": z.object({ "mode": z.any().default("in_class"), "inference_reason": z.string().min(1).max(240).default("default in-class delivery"), "teacher_override": z.boolean().default(false) }).optional(), "assessment_intent": z.array(z.string()).optional(), "research_signals": z.union([z.lazy(() => ResearchSignalsSchema), z.null()]).default(null), "teacher_preferences": z.union([z.lazy(() => TeacherPreferenceSignalsSchema), z.null()]).default(null) })


export const ResearchSignalsSchema = z.object({ "factual_risk": z.any(), "source_confidence": z.any(), "prerequisite_risk": z.any(), "misconception_refs": z.array(z.string()).optional(), "evidence_tags": z.array(z.string()).optional() })


export const TeacherPreferenceSignalsSchema = z.object({ "feedback_events": z.array(z.lazy(() => StrategyFeedbackEventSchema)).optional(), "priority_objective_ids": z.array(z.string()).optional(), "assessable_objective_ids": z.array(z.string()).optional() })


export const StrategyFeedbackEventSchema = z.object({ "event_id": z.string().min(1).max(80), "event_type": z.any(), "source": z.any(), "value": z.string().min(1).max(120), "rationale": z.union([z.string().max(500), z.null()]).default(null) })

export type ComponentStrategyResult = z.infer<typeof ComponentStrategyResultSchema>;
export type ComponentStrategyPlan = z.infer<typeof ComponentStrategyPlanSchema>;
export type StrategyVariant = z.infer<typeof StrategyVariantSchema>;
export type StrategySlot = z.infer<typeof StrategySlotSchema>;
export type StrategySlotBudget = z.infer<typeof StrategySlotBudgetSchema>;
export type ArtifactStrategyProjection = z.infer<typeof ArtifactStrategyProjectionSchema>;
export type ExportProjectionStatus = z.infer<typeof ExportProjectionStatusSchema>;
export type FallbackMetadata = z.infer<typeof FallbackMetadataSchema>;
export type StrategyQualityScore = z.infer<typeof StrategyQualityScoreSchema>;
export type StrategyBlockingIssue = z.infer<typeof StrategyBlockingIssueSchema>;
export type StrategyWarning = z.infer<typeof StrategyWarningSchema>;
export type StrategyRevision = z.infer<typeof StrategyRevisionSchema>;
export type ComponentStrategyRequest = z.infer<typeof ComponentStrategyRequestSchema>;
export type ObjectiveRef = z.infer<typeof ObjectiveRefSchema>;
export type ResearchSignals = z.infer<typeof ResearchSignalsSchema>;
export type TeacherPreferenceSignals = z.infer<typeof TeacherPreferenceSignalsSchema>;
export type StrategyFeedbackEvent = z.infer<typeof StrategyFeedbackEventSchema>;
