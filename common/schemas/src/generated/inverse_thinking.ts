/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const InverseThinkingTeacherOnlySchema = z.object({ "rationale": z.string().min(1).max(1000), "answer_key": z.string().min(1).max(1000) })


export const InverseThinkingCaseSchema = z.object({ "id": z.string().min(1).max(120), "title": z.string().min(3).max(200), "alias": z.union([z.string().max(120), z.null()]).default(null), "target_concept": z.string().min(1).max(300), "foil": z.string().min(1).max(300), "disaster": z.string().min(1).max(1000), "key_clues": z.array(z.string()).min(1).max(8), "safe_zone": z.string().min(1).max(1000), "filing_note": z.string().min(1).max(1000), "student_task": z.string().min(1).max(1000), "teacher_only": InverseThinkingTeacherOnlySchema })


export const InverseThinkingSummaryRowSchema = z.object({ "case_id": z.string().min(1).max(120), "trap": z.string().min(1).max(300), "clue": z.string().min(1).max(300), "safe_rule": z.string().min(1).max(500) })


export const InverseThinkingStudentChallengeSchema = z.object({ "id": z.string().min(1).max(120), "prompt": z.string().min(1).max(1000), "case_id": z.string().min(1).max(120) })


export const InverseThinkingPackSchema = z.object({ "methodology": z.literal("inverse_thinking"), "creative_frame": z.enum(["auto","detective_case","courtroom_trial","mythbusters_lab","survival_guide","disaster_report","custom"]), "cases": z.array(InverseThinkingCaseSchema).min(1), "summary_table": z.array(InverseThinkingSummaryRowSchema).min(1), "student_challenges": z.array(InverseThinkingStudentChallengeSchema).min(1), "teacher_only": InverseThinkingTeacherOnlySchema, "projection_hints": z.record(z.string(), z.array(z.string())).optional() })

export type InverseThinkingPack = z.infer<typeof InverseThinkingPackSchema>;
export type InverseThinkingTeacherOnly = z.infer<typeof InverseThinkingTeacherOnlySchema>;
export type InverseThinkingCase = z.infer<typeof InverseThinkingCaseSchema>;
export type InverseThinkingSummaryRow = z.infer<typeof InverseThinkingSummaryRowSchema>;
export type InverseThinkingStudentChallenge = z.infer<typeof InverseThinkingStudentChallengeSchema>;
