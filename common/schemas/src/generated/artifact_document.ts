/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ArtifactPayloadSchema = z.object({ "payload_kind": z.enum(["block_document","assessment_document"]), "sections": z.union([z.array(z.any()), z.null()]).default(null), "questions": z.union([z.array(z.any()), z.null()]).default(null) }).strict().describe("A strict block or assessment payload selected by payload_kind.")


export const DocumentSectionSchema = z.object({ "entity_id": z.string().min(1).max(80), "title": z.string().min(1).max(200), "blocks": z.array(z.lazy(() => DocumentBlockSchema)).min(1) }).describe("An ordered stable section of a block document.")


export const DocumentBlockSchema = z.object({ "entity_id": z.string().min(1).max(80), "block_kind": z.enum(["heading","paragraph"]), "text": z.string().min(1).max(10000), "level": z.union([z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4)]), z.null()]).default(null) }).strict().describe("A stable block with a validated heading or paragraph shape.")


export const AssessmentQuestionSchema = z.object({ "entity_id": z.string().min(1).max(80), "prompt": z.string().min(1).max(10000), "options": z.array(z.lazy(() => AssessmentOptionSchema)).optional() }).describe("A student-safe question that deliberately excludes answer data.")


export const AssessmentOptionSchema = z.object({ "entity_id": z.string().min(1).max(80), "text": z.string().min(1).max(2000) }).describe("A student-safe assessment option with stable identity.")


export const ArtifactDocumentSchema = z.object({ "document_id": z.string().min(1).max(80), "artifact_id": z.string().min(1).max(80), "artifact_type": z.enum(["lesson","worksheet","quiz","drill","recap","infographic","answer_key","roadmap","flashcard_deck","slide_deck","exit_ticket","reading_passage"]), "version": z.number().int().gte(1), "language": z.enum(["en","vi"]), "audience": z.enum(["student","teacher","print"]), "authority": z.enum(["generated","teacher_edit","ai_assisted_edit","restored"]), "payload": z.any(), "parent_document_id": z.union([z.string().min(1).max(80), z.null()]).default(null), "source_document_id": z.union([z.string().min(1).max(80), z.null()]).default(null) }).describe("Immutable V2 teaching artifact with an explicitly typed payload.")

export type ArtifactDocument = z.infer<typeof ArtifactDocumentSchema>;
export type ArtifactPayload = z.infer<typeof ArtifactPayloadSchema>;
export type DocumentSection = z.infer<typeof DocumentSectionSchema>;
export type DocumentBlock = z.infer<typeof DocumentBlockSchema>;
export type AssessmentQuestion = z.infer<typeof AssessmentQuestionSchema>;
export type AssessmentOption = z.infer<typeof AssessmentOptionSchema>;
