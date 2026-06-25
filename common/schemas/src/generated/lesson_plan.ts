/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const LearningObjectiveSchema = z.object({ "description": z.string().min(1).max(500), "bloom_level": z.string().regex(new RegExp("^(remember|understand|apply|analyze|evaluate|create)$")).describe("Bloom's taxonomy level"), "assessment_method": z.union([z.string().max(200), z.null()]).describe("How this objective will be assessed").default(null) }).describe("A single learning objective with Bloom's taxonomy classification.")


export const AssessmentCheckpointSchema = z.object({ "type": z.string().describe("Checkpoint type, e.g. 'exit_ticket', 'think_pair_share', 'quiz'"), "description": z.string().min(1).max(500), "trigger": z.union([z.string(), z.null()]).describe("When to trigger this checkpoint, e.g. 'after_phase_2'").default(null) }).describe("A checkpoint within the lesson for formative assessment.")


export const LessonPlanSchema = z.object({ "topic": z.string().min(1).max(200), "grade_level": z.string().describe("e.g. 'Grade 5', 'Lớp 5'"), "subject": z.string().describe("e.g. 'math', 'english', 'science'"), "duration_minutes": z.number().int().gte(10).lte(180), "learning_objectives": z.array(LearningObjectiveSchema).min(1).max(10).describe("Must cover ≥2 Bloom levels"), "prerequisite_knowledge": z.array(z.string()).optional(), "learning_plan": z.record(z.string(), z.any()).describe("Gagné 9-event phases keyed by phase name").optional(), "assessment_checkpoints": z.array(AssessmentCheckpointSchema).optional(), "methodology": z.union([z.any(), z.null()]).default(null) }).describe("Structured lesson plan output from the Planner Agent.\n\nFollows backward design (UbD) principles and Gagné's 9-event instruction model.\nBloom levels must cover at least 2 distinct levels.")

export type LessonPlan = z.infer<typeof LessonPlanSchema>;
export type LearningObjective = z.infer<typeof LearningObjectiveSchema>;
export type AssessmentCheckpoint = z.infer<typeof AssessmentCheckpointSchema>;
