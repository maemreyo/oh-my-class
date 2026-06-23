import { z } from "zod";

export const ErrorCodeSchema = z.enum([
	"VALIDATION_ERROR",
	"PIPELINE_ERROR",
	"AGENT_ERROR",
	"QUALITY_GATE_ERROR",
	"EXPORT_ERROR",
	"AUTHENTICATION_ERROR",
	"AUTHORIZATION_ERROR",
	"NOT_FOUND",
	"RATE_LIMITED",
	"INTERNAL_ERROR",
]);

export type ErrorCode = z.infer<typeof ErrorCodeSchema>;

export const ValidationErrorDetailSchema = z.object({
	field: z.string(),
	message: z.string(),
	code: z.string(),
});

export type ValidationErrorDetail = z.infer<typeof ValidationErrorDetailSchema>;

export const ErrorResponseSchema = z.object({
	error_code: ErrorCodeSchema,
	message: z.string().min(1).max(500),
	request_id: z.string().optional(),
	timestamp: z.string().optional(),
	details: z.array(ValidationErrorDetailSchema).default([]),
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

export const PipelineErrorResponseSchema = ErrorResponseSchema.extend({
	run_id: z.string().optional(),
	step: z.number().int().optional(),
	agent: z.string().optional(),
});

export type PipelineErrorResponse = z.infer<typeof PipelineErrorResponseSchema>;
