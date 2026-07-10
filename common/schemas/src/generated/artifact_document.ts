/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const BlockDocumentSchema = z.object({ "payload_kind": z.literal("block_document").default("block_document"), "sections": z.array(z.lazy(() => DocumentSectionSchema)).min(1) }).describe("Typed payload for lesson-like and synthesis artifact surfaces.")


export const DocumentSectionSchema = z.object({ "entity_id": z.string().min(1).max(80), "title": z.string().min(1).max(200), "blocks": z.array(z.any().superRefine((x, ctx) => {
    const schemas = [z.any(), z.any()];
    const { errors, failed } = schemas.reduce<{
      errors: z.core.$ZodIssue[];
      failed: number;
    }>(
      ({ errors, failed }, schema) =>
        ((result) =>
          result.error
            ? {
                errors: [...errors, ...result.error.issues],
                failed: failed + 1,
              }
            : { errors, failed })(
          schema.safeParse(x),
        ),
      { errors: [], failed: 0 },
    );
    const passed = schemas.length - failed;
    if (passed !== 1) {
      ctx.addIssue(errors.length ? {
        path: [],
        code: "invalid_union",
        errors: [errors],
        message: "Invalid input: Should pass single schema. Passed " + passed,
      } : {
        path: [],
        code: "custom",
        errors: [errors],
        message: "Invalid input: Should pass single schema. Passed " + passed,
      });
    }
  })).min(1) }).describe("An ordered stable section of a block document.")


export const HeadingBlockSchema = z.object({ "entity_id": z.string().min(1).max(80), "block_kind": z.literal("heading").default("heading"), "level": z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4)]), "text": z.string().min(1).max(2000) }).describe("A stable heading in a block document.")


export const ParagraphBlockSchema = z.object({ "entity_id": z.string().min(1).max(80), "block_kind": z.literal("paragraph").default("paragraph"), "text": z.string().min(1).max(10000) }).describe("A stable paragraph in a block document.")


export const AssessmentDocumentSchema = z.object({ "payload_kind": z.literal("assessment_document").default("assessment_document"), "questions": z.array(z.lazy(() => AssessmentQuestionSchema)).min(1) }).describe("Typed student-safe payload for question-bearing artifacts.")


export const AssessmentQuestionSchema = z.object({ "entity_id": z.string().min(1).max(80), "prompt": z.string().min(1).max(10000), "options": z.array(z.lazy(() => AssessmentOptionSchema)).optional() }).describe("A student-safe question that deliberately excludes answer data.")


export const AssessmentOptionSchema = z.object({ "entity_id": z.string().min(1).max(80), "text": z.string().min(1).max(2000) }).describe("A student-safe assessment option with stable identity.")


export const ArtifactDocumentSchema = z.object({ "document_id": z.string().min(1).max(80), "artifact_id": z.string().min(1).max(80), "artifact_type": z.enum(["lesson","worksheet","quiz","drill","recap","infographic","answer_key","roadmap","flashcard_deck","slide_deck","exit_ticket","reading_passage"]), "version": z.number().int().gte(1), "language": z.enum(["en","vi"]), "audience": z.enum(["student","teacher","print"]), "authority": z.enum(["generated","teacher_edit","ai_assisted_edit","restored"]), "payload": z.any().superRefine((x, ctx) => {
    const schemas = [z.any(), z.any()];
    const { errors, failed } = schemas.reduce<{
      errors: z.core.$ZodIssue[];
      failed: number;
    }>(
      ({ errors, failed }, schema) =>
        ((result) =>
          result.error
            ? {
                errors: [...errors, ...result.error.issues],
                failed: failed + 1,
              }
            : { errors, failed })(
          schema.safeParse(x),
        ),
      { errors: [], failed: 0 },
    );
    const passed = schemas.length - failed;
    if (passed !== 1) {
      ctx.addIssue(errors.length ? {
        path: [],
        code: "invalid_union",
        errors: [errors],
        message: "Invalid input: Should pass single schema. Passed " + passed,
      } : {
        path: [],
        code: "custom",
        errors: [errors],
        message: "Invalid input: Should pass single schema. Passed " + passed,
      });
    }
  }), "parent_document_id": z.union([z.string().min(1).max(80), z.null()]).default(null), "source_document_id": z.union([z.string().min(1).max(80), z.null()]).default(null) }).describe("Immutable V2 teaching artifact with an explicitly typed payload.")

export type ArtifactDocument = z.infer<typeof ArtifactDocumentSchema>;
export type BlockDocument = z.infer<typeof BlockDocumentSchema>;
export type DocumentSection = z.infer<typeof DocumentSectionSchema>;
export type HeadingBlock = z.infer<typeof HeadingBlockSchema>;
export type ParagraphBlock = z.infer<typeof ParagraphBlockSchema>;
export type AssessmentDocument = z.infer<typeof AssessmentDocumentSchema>;
export type AssessmentQuestion = z.infer<typeof AssessmentQuestionSchema>;
export type AssessmentOption = z.infer<typeof AssessmentOptionSchema>;
