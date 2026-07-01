/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const VocabularyClusterWorkflowSchema = z.object({ "workflow_id": z.string().min(1).max(120), "cluster_id": z.string().min(1).max(120), "run_id": z.string().min(1).max(120), "normalized_input": z.array(z.string()).min(1), "raw_input_span": z.string().min(1).max(2000), "status": z.enum(["queued","grounding","synthesizing","practice_generating","validating","needs_review","passed","failed","skipped","exported"]), "attempts": z.number().int().gte(0).lte(20), "review_status": z.enum(["pending","needs_review","approved","rejected"]), "export_refs": z.record(z.string(), z.string()).optional(), "snapshot_hash": z.union([z.string().min(64).max(64), z.null()]).default(null), "last_error": z.union([z.string().max(1000), z.null()]).default(null) })




export const VocabularyClusterEvidenceEntrySchema = z.object({ "evidence_id": z.string().min(1).max(120), "workflow_id": z.string().min(1).max(120), "cluster_id": z.string().min(1).max(120), "run_id": z.string().min(1).max(120), "sequence": z.number().int().gte(1), "event_type": z.enum(["normalized_input","grounding_sources","generated_contract_version","quality_result","teacher_edit","approval","export_ref","retry"]), "payload": z.any() })

export type VocabularyClusterWorkflow = z.infer<typeof VocabularyClusterWorkflowSchema>;
export type VocabularyClusterEvidenceEntry = z.infer<typeof VocabularyClusterEvidenceEntrySchema>;
