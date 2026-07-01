/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const AnchorCardSchema = z.object({ "word": z.string().min(1).max(120), "impression_vi": z.string().min(1).max(300), "core_trigger_en": z.string().min(1).max(120), "visual_cue_vi": z.string().min(1).max(300), "semantic_chain": z.array(z.string()).min(1).max(8), "example_en": z.string().min(1).max(500), "contrast_note_vi": z.string().min(1).max(500), "student_explanation_vi": z.string().min(1).max(700), "teacher_script_vi": z.string().min(1).max(1000), "edge_cases": z.array(z.string()).default([]), "source_notes": z.array(z.string()).default([]) })


export const SemanticAnchorClusterSchema = z.object({ "cluster_id": z.string().min(1).max(120), "title": z.string().min(1).max(200), "title_confidence": z.number().gte(0).lte(1), "raw_input_span": z.string().min(1).max(1000), "terms": z.array(z.string()).min(2), "anchors": z.array(z.lazy(() => AnchorCardSchema)).min(1), "contrast_notes": z.array(z.string()).min(1), "summary_rows": z.array(z.string()).min(1), "review_status": z.enum(["passed","needs_review","failed"]), "warnings": z.array(z.string()).default([]), "teacher_source_notes": z.array(z.string()).default([]) })




export const PracticeItemSchema = z.object({ "item_id": z.string().min(1).max(120), "intent": z.enum(["core_trigger_recall","context_discrimination","boundary_explanation","reverse_retrieval"]), "prompt": z.string().min(1).max(1000), "answer": z.string().min(1).max(500), "rationale": z.string().min(1).max(1000) })


export const PracticeSetSchema = z.object({ "practice_set_id": z.string().min(1).max(120), "cluster_id": z.string().min(1).max(120), "items": z.array(z.lazy(() => PracticeItemSchema)).min(1) })


export const ClusterProjectionRefsSchema = z.object({ "cluster_id": z.string().min(1).max(120), "teaching_teacher_html": z.string().min(1).max(500), "teaching_student_html": z.string().min(1).max(500), "practice_teacher_html": z.string().min(1).max(500), "practice_student_html": z.string().min(1).max(500) })


export const ClusterExportPolicySchema = z.object({ "passed": z.array(z.enum(["teacher_teaching_html","student_teaching_html","teacher_practice_html","student_practice_html","teacher_review_html","diagnostic_report","gift","h5p"])).min(1), "needs_review": z.array(z.enum(["teacher_teaching_html","student_teaching_html","teacher_practice_html","student_practice_html","teacher_review_html","diagnostic_report","gift","h5p"])).min(1), "failed": z.array(z.enum(["teacher_teaching_html","student_teaching_html","teacher_practice_html","student_practice_html","teacher_review_html","diagnostic_report","gift","h5p"])).min(1) })


export const VocabularyBatchConfigSchema = z.object({ "batch_id": z.string().min(1).max(120), "teacher_id": z.string().min(1).max(120), "locale": z.string().min(2).max(16), "target_cefr": z.union([z.string().max(16), z.null()]).default(null), "max_clusters": z.number().int().gte(1).lte(100), "default_export_policy": z.lazy(() => ClusterExportPolicySchema) })


export const NormalizedVocabularyClusterSchema = z.object({ "cluster_id": z.string().min(1).max(120), "terms": z.array(z.string()).min(2), "raw_input_span": z.string().min(1).max(1000), "title_hint": z.union([z.string().max(200), z.null()]).default(null), "notes": z.array(z.string()).default([]), "confidence": z.number().gte(0).lte(1) })


export const AmbiguousVocabularyClusterSchema = z.object({ "span_id": z.string().min(1).max(120), "raw_input_span": z.string().min(1).max(1000), "terms": z.array(z.string()).default([]), "reason": z.string().min(1).max(500), "confidence": z.number().gte(0).lte(1) })


export const InputNormalizationReportSchema = z.object({ "report_id": z.string().min(1).max(120), "ready_clusters": z.array(z.lazy(() => NormalizedVocabularyClusterSchema)).default([]), "ambiguous_clusters": z.array(z.lazy(() => AmbiguousVocabularyClusterSchema)).default([]), "clarifying_questions": z.array(z.string()).default([]), "skipped_spans": z.array(z.string()).default([]), "parse_confidence": z.number().gte(0).lte(1) })


export const LexicalGroundingSourceEvidenceSchema = z.object({ "source_id": z.string().min(1).max(120), "title": z.string().min(1).max(500), "url": z.union([z.string().max(2000), z.null()]).default(null), "excerpt": z.string().min(1).max(2000), "verification_status": z.enum(["VERIFIED","MODIFIED","REMOVED","UNCERTAIN"]) })


export const LexicalGroundingRequestSchema = z.object({ "cluster": z.lazy(() => NormalizedVocabularyClusterSchema), "source_evidence": z.array(z.lazy(() => LexicalGroundingSourceEvidenceSchema)).default([]), "cluster_snapshot_hash": z.string().min(1).max(120) })


export const LexicalTermDefinitionSchema = z.object({ "term": z.string().min(1).max(120), "definition": z.string().min(1).max(700), "source_ids": z.array(z.string()).min(1), "confidence": z.number().gte(0).lte(1) })


export const LexicalUsageConstraintSchema = z.object({ "term": z.string().min(1).max(120), "constraint": z.string().min(1).max(700), "source_ids": z.array(z.string()).min(1), "confidence": z.number().gte(0).lte(1) })


export const LexicalExamplePairSchema = z.object({ "term": z.string().min(1).max(120), "example": z.string().min(1).max(700), "counterexample": z.string().min(1).max(700), "contrast_note": z.string().min(1).max(700), "source_ids": z.array(z.string()).min(1) })


export const LexicalGroundingCacheKeysSchema = z.object({ "cluster_snapshot_key": z.string().min(1).max(200), "term_distinction_key": z.string().min(1).max(500) })


export const LexicalGroundingBundleSchema = z.object({ "bundle_id": z.string().min(1).max(120), "cluster_id": z.string().min(1).max(120), "terms": z.array(z.string()).min(2), "source_ids": z.array(z.string()).min(1), "term_definitions": z.array(z.lazy(() => LexicalTermDefinitionSchema)).default([]), "usage_constraints": z.array(z.lazy(() => LexicalUsageConstraintSchema)).default([]), "common_confusions": z.array(z.string()).default([]), "example_pairs": z.array(z.lazy(() => LexicalExamplePairSchema)).default([]), "distinction_notes": z.array(z.string()).min(1), "teacher_source_notes": z.array(z.string()).default([]), "student_projection_fields": z.array(z.enum(["term_definitions","usage_constraints","common_confusions","example_pairs","distinction_notes"])).default([]), "confidence": z.number().gte(0).lte(1), "readiness": z.enum(["passed","needs_review","failed"]), "cache_keys": z.lazy(() => LexicalGroundingCacheKeysSchema), "uncertainty_flags": z.array(z.string()).default([]) })

export type SemanticAnchorCluster = z.infer<typeof SemanticAnchorClusterSchema>;
export type AnchorCard = z.infer<typeof AnchorCardSchema>;
export type PracticeItem = z.infer<typeof PracticeItemSchema>;
export type PracticeSet = z.infer<typeof PracticeSetSchema>;
export type ClusterProjectionRefs = z.infer<typeof ClusterProjectionRefsSchema>;
export type ClusterExportPolicy = z.infer<typeof ClusterExportPolicySchema>;
export type VocabularyBatchConfig = z.infer<typeof VocabularyBatchConfigSchema>;
export type NormalizedVocabularyCluster = z.infer<typeof NormalizedVocabularyClusterSchema>;
export type AmbiguousVocabularyCluster = z.infer<typeof AmbiguousVocabularyClusterSchema>;
export type InputNormalizationReport = z.infer<typeof InputNormalizationReportSchema>;
export type LexicalGroundingSourceEvidence = z.infer<typeof LexicalGroundingSourceEvidenceSchema>;
export type LexicalGroundingRequest = z.infer<typeof LexicalGroundingRequestSchema>;
export type LexicalTermDefinition = z.infer<typeof LexicalTermDefinitionSchema>;
export type LexicalUsageConstraint = z.infer<typeof LexicalUsageConstraintSchema>;
export type LexicalExamplePair = z.infer<typeof LexicalExamplePairSchema>;
export type LexicalGroundingCacheKeys = z.infer<typeof LexicalGroundingCacheKeysSchema>;
export type LexicalGroundingBundle = z.infer<typeof LexicalGroundingBundleSchema>;
