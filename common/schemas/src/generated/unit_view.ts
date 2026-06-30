/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"
import { LessonSequenceSchema } from "./lesson_sequence.js"

export const UnitParentMetaSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "parent_run_id": z.string().min(1).max(64), "teacher_id": z.string().min(1).max(64), "topic": z.string().min(1).max(200) })


export const UnitSessionProgressSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "session_id": z.string().min(1).max(32), "child_run_id": z.union([z.string().max(64), z.null()]).default(null), "status": z.enum(["pending","generating","in_review","approved","failed","blocked"]), "progress_percent": z.number().int().gte(0).lte(100) })


export const UnitAggregateSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "status": z.enum(["awaiting_unit_approval","preparing","generating","in_review","partially_complete","complete"]), "total_sessions": z.number().int().gte(1).lte(20), "approved_sessions": z.number().int().gte(0).lte(20), "failed_sessions": z.number().int().gte(0).lte(20) })


export const UnitCoherenceWarningSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "code": z.string().min(1).max(64), "message": z.string().min(1).max(500), "session_ids": z.array(z.string()).optional() })


export const UnitViewSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "parent": z.lazy(() => UnitParentMetaSchema), "sequence": LessonSequenceSchema, "sessions": z.array(z.lazy(() => UnitSessionProgressSchema)).min(1).max(20), "aggregate": z.lazy(() => UnitAggregateSchema), "coherence_warnings": z.array(z.lazy(() => UnitCoherenceWarningSchema)).optional(), "cursor": z.number().int().gte(0) })




export const UnitSessionStatusEventSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "session": z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "session_id": z.string().min(1).max(32), "child_run_id": z.union([z.string().max(64), z.null()]).default(null), "status": z.enum(["pending","generating","in_review","approved","failed","blocked"]), "progress_percent": z.number().int().gte(0).lte(100) }) })


export const UnitAggregateEventSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "aggregate": z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "status": z.enum(["awaiting_unit_approval","preparing","generating","in_review","partially_complete","complete"]), "total_sessions": z.number().int().gte(1).lte(20), "approved_sessions": z.number().int().gte(0).lte(20), "failed_sessions": z.number().int().gte(0).lte(20) }) })


export const UnitCoherenceWarningEventSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "warning": z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "code": z.string().min(1).max(64), "message": z.string().min(1).max(500), "session_ids": z.array(z.string()).optional() }) })


export const UnitEventEnvelopeSchema = z.object({ "schema_version": z.literal("unit_view.v1").default("unit_view.v1"), "event_type": z.enum(["unit_aggregate_changed","unit_session_changed","unit_coherence_warning"]), "parent_run_id": z.string().min(1).max(64), "cursor": z.number().int().gte(1), "payload": z.union([z.any(), z.any(), z.any()]) })

export type UnitView = z.infer<typeof UnitViewSchema>;
export type UnitParentMeta = z.infer<typeof UnitParentMetaSchema>;
export type UnitSessionProgress = z.infer<typeof UnitSessionProgressSchema>;
export type UnitAggregate = z.infer<typeof UnitAggregateSchema>;
export type UnitCoherenceWarning = z.infer<typeof UnitCoherenceWarningSchema>;
export type UnitSessionStatusEvent = z.infer<typeof UnitSessionStatusEventSchema>;
export type UnitAggregateEvent = z.infer<typeof UnitAggregateEventSchema>;
export type UnitCoherenceWarningEvent = z.infer<typeof UnitCoherenceWarningEventSchema>;
export type UnitEventEnvelope = z.infer<typeof UnitEventEnvelopeSchema>;
