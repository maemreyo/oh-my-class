/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const ValidationErrorDetailSchema = z.object({ "field": z.string().describe("Dotted path to the failing field, e.g. 'title'"), "message": z.string().describe("Human-readable explanation of the failure"), "code": z.string().describe("Machine-readable code, e.g. 'min_length'") }).describe("A single field-level validation failure.\n\nReturned inside ErrorResponse.details when the error code is\nVALIDATION_ERROR. Multiple details may be returned in one response\nto report all failing fields at once.")


export const ErrorResponseSchema = z.object({ "error_code": z.any().describe("Machine-readable error category"), "message": z.string().min(1).max(500).describe("Human-readable error message"), "request_id": z.union([z.string(), z.null()]).describe("Correlation ID for distributed tracing").default(null), "timestamp": z.union([z.string(), z.null()]).describe("ISO 8601 timestamp of when the error occurred").default(null), "details": z.array(z.lazy(() => ValidationErrorDetailSchema)).describe("Field-level validation details; empty for non-validation errors").optional() }).describe("Standard error envelope returned by every API endpoint.\n\nClients should switch on error_code to determine recovery strategy.\nThe message field is safe to display to end users.")




export const PipelineErrorResponseSchema = z.object({ "error_code": z.enum(["VALIDATION_ERROR","PIPELINE_ERROR","AGENT_ERROR","QUALITY_GATE_ERROR","EXPORT_ERROR","AUTHENTICATION_ERROR","AUTHORIZATION_ERROR","NOT_FOUND","RATE_LIMITED","INTERNAL_ERROR"]).describe("Machine-readable error categories.\n\nEvery error response must carry one of these codes so that clients\ncan dispatch recovery logic without parsing the human message."), "message": z.string().min(1).max(500).describe("Human-readable error message"), "request_id": z.union([z.string(), z.null()]).describe("Correlation ID for distributed tracing").default(null), "timestamp": z.union([z.string(), z.null()]).describe("ISO 8601 timestamp of when the error occurred").default(null), "details": z.array(z.object({ "field": z.string().describe("Dotted path to the failing field, e.g. 'title'"), "message": z.string().describe("Human-readable explanation of the failure"), "code": z.string().describe("Machine-readable code, e.g. 'min_length'") }).describe("A single field-level validation failure.\n\nReturned inside ErrorResponse.details when the error code is\nVALIDATION_ERROR. Multiple details may be returned in one response\nto report all failing fields at once.")).describe("Field-level validation details; empty for non-validation errors").optional(), "run_id": z.union([z.string(), z.null()]).describe("Pipeline run identifier").default(null), "step": z.union([z.number().int(), z.null()]).describe("Pipeline step number (1-13) where the error occurred").default(null), "agent": z.union([z.string(), z.null()]).describe("Agent that produced the error (e.g. 'planner')").default(null) }).describe("Error response specialised for pipeline and agent failures.\n\nExtends ErrorResponse with fields that identify which pipeline run,\nstep, and agent produced the error — essential for debugging the\n13-step pipeline.")

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
export type ValidationErrorDetail = z.infer<typeof ValidationErrorDetailSchema>;
export type PipelineErrorResponse = z.infer<typeof PipelineErrorResponseSchema>;
