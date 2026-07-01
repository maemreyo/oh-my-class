/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ContractRevisionMetaSchema = z.object({ "revision": z.number().int().gte(1), "actor": z.enum(["system","teacher","admin"]), "source": z.enum(["code_defaults","policy","env","request","teacher","admin"]), "reason": z.string().min(1).max(200), "effective_stage": z.string().min(1).max(64) })


export const DecompositionIntentSchema = z.object({ "schema_version": z.literal("decomposition_intent.v1").default("decomposition_intent.v1"), "target_sessions": z.number().int().gte(1).lte(20), "session_length_minutes": z.number().int().gte(10).lte(90), "source": z.enum(["teacher","system","admin"]), "rationale": z.string().min(1).max(500) })


export const RunContractSchema = z.object({ "contract_id": z.string().min(1).max(64), "run_id": z.string().min(1).max(64), "teacher_id": z.string().min(1).max(64), "mode": z.enum(["generate_pack","diagnose_then_generate","plan_unit","vocabulary_batch"]).default("generate_pack"), "topic": z.string().min(1).max(200), "grade_band": z.string().min(1).max(64), "subject": z.string().min(1).max(80), "locale": z.string().min(2).max(16), "instruction_language": z.string().min(2).max(32), "curriculum": z.union([z.string().max(80), z.null()]).default(null), "citation_locale": z.string().min(2).max(16), "artifact_types": z.array(z.enum(["lesson","worksheet","quiz","drill","recap","infographic"])).min(1), "export_formats": z.array(z.enum(["html","gift","h5p","qti","anki_apkg","flashcard_tsv","google_forms"])).min(1), "research_policy": z.enum(["basic","standard","rigorous"]).default("standard"), "config_version": z.string().min(1).max(64), "config_hash": z.string().min(64).max(64), "student_evidence": z.union([z.any(), z.null()]).default(null), "decomposition_intent": z.union([z.lazy(() => DecompositionIntentSchema), z.null()]).default(null), "revision_meta": z.lazy(() => ContractRevisionMetaSchema) })




export const ContractRevisionSchema = z.object({ "contract_id": z.string().min(1).max(64), "run_id": z.string().min(1).max(64), "contract": z.lazy(() => RunContractSchema), "revision_meta": z.object({ "revision": z.number().int().gte(1), "actor": z.enum(["system","teacher","admin"]), "source": z.enum(["code_defaults","policy","env","request","teacher","admin"]), "reason": z.string().min(1).max(200), "effective_stage": z.string().min(1).max(64) }) })

export type RunContract = z.infer<typeof RunContractSchema>;
export type ContractRevisionMeta = z.infer<typeof ContractRevisionMetaSchema>;
export type DecompositionIntent = z.infer<typeof DecompositionIntentSchema>;
export type ContractRevision = z.infer<typeof ContractRevisionSchema>;
