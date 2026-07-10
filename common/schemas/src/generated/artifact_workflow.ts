/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"
import { RunContractSchema } from "./run_contract.js"
import { ResearchBriefSchema } from "./research_brief.js"
import { ArtifactResearchGuidanceSchema } from "./research_brief.js"

export const ArtifactWorkflowStateSchema = z.object({ "workflow_id": z.string().min(1).max(64), "run_id": z.string().min(1).max(64), "artifact_id": z.string().min(1).max(64), "artifact_type": z.enum(["lesson","worksheet","quiz","drill","recap","flashcard_deck","answer_key","roadmap","slide_deck","exit_ticket","reading_passage","infographic"]), "status": z.enum(["queued","running","validating","healing","passed","failed","skipped","escalated"]), "attempts": z.number().int().gte(0), "contract_revision_id": z.number().int().gte(1), "research_guidance_id": z.string().min(1).max(64), "validation_status": z.enum(["pending","passed","failed","skipped"]).default("pending"), "judge_status": z.enum(["pending","passed","failed","skipped"]).default("pending"), "snapshot_refs": z.array(z.string()).optional(), "last_error": z.union([z.string().max(500), z.null()]).default(null) })




export const ArtifactGenerationInputSchema = z.object({ "artifact_type": z.enum(["lesson","worksheet","quiz","drill","recap","flashcard_deck","answer_key","roadmap","slide_deck","exit_ticket","reading_passage","infographic"]), "lesson_blueprint": z.any(), "contract": RunContractSchema, "research_brief": ResearchBriefSchema, "research_guidance": ArtifactResearchGuidanceSchema, "visual_spec": z.any(), "dependencies": z.array(z.enum(["lesson","worksheet","quiz","drill","recap","flashcard_deck","answer_key","roadmap","slide_deck","exit_ticket","reading_passage","infographic"])).optional() })

export type ArtifactWorkflowState = z.infer<typeof ArtifactWorkflowStateSchema>;
export type ArtifactGenerationInput = z.infer<typeof ArtifactGenerationInputSchema>;
