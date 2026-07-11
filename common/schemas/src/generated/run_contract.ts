/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ContractRevisionMetaSchema = z.object({ "revision": z.number().int().gte(1), "actor": z.enum(["system","teacher","admin"]), "source": z.enum(["code_defaults","policy","env","request","teacher","admin"]), "reason": z.string().min(1).max(200), "effective_stage": z.string().min(1).max(64) })


export const DecompositionIntentSchema = z.object({ "schema_version": z.literal("decomposition_intent.v1").default("decomposition_intent.v1"), "target_sessions": z.number().int().gte(1).lte(20), "session_length_minutes": z.number().int().gte(10).lte(90), "source": z.enum(["teacher","system","admin"]), "rationale": z.string().min(1).max(500) })


export const RunContractSchema = z.object({ "contract_id": z.string().min(1).max(64), "run_id": z.string().min(1).max(64), "teacher_id": z.string().min(1).max(64), "mode": z.enum(["generate_pack","diagnose_then_generate","plan_unit","vocabulary_batch"]).default("generate_pack"), "topic": z.string().min(1).max(200), "education_policy_version": z.literal("education_policy.v1").default("education_policy.v1"), "grade_band": z.enum(["k_2","grades_3_5","grades_6_8","grades_9_12"]), "subject": z.enum(["english","geography","history","informatics","language_arts","literature","math","science","vietnamese"]), "locale": z.string().min(2).max(16), "target_language": z.enum(["en","vi"]).default("en"), "instruction_language": z.enum(["en","vi"]), "curriculum": z.union([z.string().max(80), z.null()]).default(null), "curriculum_framework": z.enum(["ccss","general","moet_2018","ngss"]).default("general"), "citation_locale": z.string().min(2).max(16), "artifact_types": z.array(z.enum(["lesson","worksheet","quiz","drill","recap","infographic","flashcard_deck","answer_key","roadmap","slide_deck","reading_passage","exit_ticket"])).min(1), "export_formats": z.array(z.enum(["html","gift","h5p","qti","anki_apkg","flashcard_tsv","pptx"])).min(1), "publish_targets": z.array(z.literal("google_forms")).optional(), "research_policy": z.enum(["basic","standard","rigorous"]).default("standard"), "config_version": z.string().min(1).max(64), "config_hash": z.string().min(64).max(64), "student_evidence": z.union([z.any(), z.null()]).default(null), "decomposition_intent": z.union([z.lazy(() => DecompositionIntentSchema), z.null()]).default(null), "revision_meta": z.lazy(() => ContractRevisionMetaSchema) })




export const ContractRevisionSchema = z.object({ "contract_id": z.string().min(1).max(64), "run_id": z.string().min(1).max(64), "contract": z.lazy(() => RunContractSchema), "revision_meta": z.object({ "revision": z.number().int().gte(1), "actor": z.enum(["system","teacher","admin"]), "source": z.enum(["code_defaults","policy","env","request","teacher","admin"]), "reason": z.string().min(1).max(200), "effective_stage": z.string().min(1).max(64) }) })

export type RunContract = z.infer<typeof RunContractSchema>;
export type ContractRevisionMeta = z.infer<typeof ContractRevisionMetaSchema>;
export type DecompositionIntent = z.infer<typeof DecompositionIntentSchema>;
export type ContractRevision = z.infer<typeof ContractRevisionSchema>;
