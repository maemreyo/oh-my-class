/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const LayerScoreSchema = z.object({ "layer": z.string().describe("Layer name: 'format_compliance', 'content_quality', or 'presentation'"), "score": z.number().gte(0).lte(10), "weight": z.number().gte(0).lte(1).describe("Weight for this layer in the overall score (must sum to 1.0)"), "issues": z.array(z.string()).optional() }).describe("Score for a single quality layer in the G-Eval framework.")


export const JudgeOutputSchema = z.object({ "overall_score": z.number().gte(0).lte(10), "layer_scores": z.array(z.lazy(() => LayerScoreSchema)).optional(), "critical_issues": z.array(z.string()).describe("Issues that auto-fail regardless of score").optional(), "passed": z.boolean().describe("True if overall_score >= 7.0 and no critical issues"), "rationale": z.string().min(1).describe("Think-before-score rationale (written before numeric scores)") }).describe("Final judgment output from the Reviewer Agent.\n\nProduced by 3 independent judge calls; majority vote determines the final score.\nPass threshold: overall_score >= 7.0 AND no critical issues.")

export type JudgeOutput = z.infer<typeof JudgeOutputSchema>;
export type LayerScore = z.infer<typeof LayerScoreSchema>;
