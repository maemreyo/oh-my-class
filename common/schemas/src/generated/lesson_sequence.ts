/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const SessionPlanSchema = z.object({ "schema_version": z.literal("lesson_sequence.v1").default("lesson_sequence.v1"), "session_id": z.string().min(1).max(32), "order_index": z.number().int().gte(1).lte(20), "child_run_id": z.union([z.string().max(64), z.null()]).default(null), "title": z.string().min(1).max(200), "sub_topic": z.string().min(1).max(200), "duration_minutes": z.number().int().gte(10).lte(90), "learning_objectives": z.array(z.string()).min(1).max(5), "bloom_level_primary": z.enum(["remember","understand","apply","analyze","evaluate","create"]), "knowledge_components": z.array(z.lazy(() => KnowledgeComponentSchema)).max(4).optional(), "recalled_kc_ids": z.array(z.string()).optional(), "prerequisite_sessions": z.array(z.string()).optional(), "methodology_primary": z.enum(["concept_map","contrastive_pairs","film_based","shy_student_1on1","active_recall","why_wrong_reasoning","timed_quiz","roleplay_script","inverse_thinking","semantic_anchoring"]), "methodology_secondary": z.union([z.enum(["concept_map","contrastive_pairs","film_based","shy_student_1on1","active_recall","why_wrong_reasoning","timed_quiz","roleplay_script","inverse_thinking","semantic_anchoring"]), z.null()]).default(null) })


export const KnowledgeComponentSchema = z.object({ "schema_version": z.literal("lesson_sequence.v1").default("lesson_sequence.v1"), "kc_id": z.string().min(1).max(64), "title": z.string().min(1).max(160), "description": z.string().min(1).max(500) })


export const PrerequisiteEdgeSchema = z.object({ "schema_version": z.literal("lesson_sequence.v1").default("lesson_sequence.v1"), "source_kc_id": z.string().min(1).max(64), "target_kc_id": z.string().min(1).max(64), "rationale": z.string().min(1).max(300) })


export const LessonSequenceSchema = z.object({ "schema_version": z.literal("lesson_sequence.v1").default("lesson_sequence.v1"), "topic": z.string().min(1).max(200), "grade_level": z.string().min(1).max(64), "subject": z.string().min(1).max(80), "locale": z.string().min(2).max(16), "total_sessions": z.number().int().gte(1).lte(20), "total_duration_minutes": z.number().int().gte(10).lte(1800), "sessions": z.array(z.lazy(() => SessionPlanSchema)).min(1).max(20), "prerequisite_edges": z.array(z.lazy(() => PrerequisiteEdgeSchema)).optional(), "grounding_status": z.enum(["grounded","partial","ungrounded"]), "confidence": z.number().gte(0).lte(1), "open_questions": z.array(z.string()).optional(), "low_confidence_decisions": z.array(z.string()).optional(), "rationale": z.string().min(1).max(2000) })

export type LessonSequence = z.infer<typeof LessonSequenceSchema>;
export type SessionPlan = z.infer<typeof SessionPlanSchema>;
export type KnowledgeComponent = z.infer<typeof KnowledgeComponentSchema>;
export type PrerequisiteEdge = z.infer<typeof PrerequisiteEdgeSchema>;
