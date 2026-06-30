/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const EvidenceCitationSchema = z.object({ "source_id": z.string().min(1).max(64), "title": z.string().min(1).max(500), "url": z.string().min(1).max(2000), "domain": z.string().min(1).max(255), "credibility_score": z.number().gte(0).lte(1) })


export const ArtifactResearchGuidanceSchema = z.object({ "artifact_type": z.string().min(1).max(64), "guidance": z.array(z.string()).optional(), "citation_ids": z.array(z.string()).optional() })


export const ResearchBriefSchema = z.object({ "topic": z.string().min(1).max(200), "subject": z.string().min(1).max(80), "key_findings": z.array(z.string()).optional(), "citations": z.array(z.lazy(() => EvidenceCitationSchema)).optional(), "artifact_guidance": z.array(z.lazy(() => ArtifactResearchGuidanceSchema)).optional(), "research_policy": z.enum(["basic","standard","rigorous"]).default("standard") })




export const PrePlanningSearchBriefSchema = z.object({ "topic": z.string().min(1).max(200), "subject": z.string().min(1).max(80), "risk_level": z.enum(["low","medium","high"]), "query_count": z.number().int().gte(0).lte(20), "confirmation_reasons": z.array(z.string()).default([]) })

export type ResearchBrief = z.infer<typeof ResearchBriefSchema>;
export type EvidenceCitation = z.infer<typeof EvidenceCitationSchema>;
export type ArtifactResearchGuidance = z.infer<typeof ArtifactResearchGuidanceSchema>;
export type PrePlanningSearchBrief = z.infer<typeof PrePlanningSearchBriefSchema>;
