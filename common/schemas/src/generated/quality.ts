/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const QualityIssueSchema = z.object({ "failure_class": z.any(), "location": z.string(), "message": z.string(), "hard_block": z.boolean().default(true) })


export const ArtifactQualityReportSchema = z.object({ "artifact_id": z.string(), "artifact_type": z.string(), "education_policy_version": z.string().default("education_policy.v1"), "passed": z.boolean(), "issues": z.array(z.lazy(() => QualityIssueSchema)).optional() })




export const HealingDecisionSchema = z.object({ "failure_class": z.enum(["schema_invalid","placeholder_content","answer_key_leakage","pii_leakage","external_asset","missing_doctype","missing_accessibility","unsupported_component","factual_uncertainty","pedagogical_mismatch","export_not_ready"]), "strategy": z.any(), "max_attempts": z.number().int() })


export const ExportReadinessReportSchema = z.object({ "run_id": z.string(), "education_policy_version": z.string().default("education_policy.v1"), "passed": z.boolean(), "approved_snapshot_ids": z.array(z.string()).optional(), "issues": z.array(z.object({ "failure_class": z.any(), "location": z.string(), "message": z.string(), "hard_block": z.boolean().default(true) })).optional() })

export type ArtifactQualityReport = z.infer<typeof ArtifactQualityReportSchema>;
export type QualityIssue = z.infer<typeof QualityIssueSchema>;
export type HealingDecision = z.infer<typeof HealingDecisionSchema>;
export type ExportReadinessReport = z.infer<typeof ExportReadinessReportSchema>;
