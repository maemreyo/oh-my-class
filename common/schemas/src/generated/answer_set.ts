/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const AnswerEntrySchema = z.object({ "entity_id": z.string().min(1).max(80), "question_id": z.string().min(1).max(80), "correct_option_ids": z.array(z.string()).optional(), "accepted_answers": z.array(z.string()).optional(), "rationale": z.union([z.string().min(1).max(2000), z.null()]).default(null) }).describe("One teacher-only answer for a question in an assessment document.")


export const AnswerSetSchema = z.object({ "answer_set_id": z.string().min(1).max(80), "source_document_id": z.string().min(1).max(80), "source_version": z.number().int().gte(1), "authority": z.enum(["generated","teacher_edit","ai_assisted_edit"]).default("generated"), "entries": z.array(z.lazy(() => AnswerEntrySchema)).min(1) }).describe("Teacher-only answers for one immutable assessment document version.")

export type AnswerSet = z.infer<typeof AnswerSetSchema>;
export type AnswerEntry = z.infer<typeof AnswerEntrySchema>;
