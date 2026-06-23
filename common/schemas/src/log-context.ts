import { z } from "zod";

export const LogContextSchema = z.object({
	request_id: z.string().default(""),
	teacher_id: z.string().default(""),
	run_id: z.string().default(""),
	step: z.number().int().optional(),
	agent: z.string().optional(),
	timestamp: z.string().default(""),
});

export type LogContext = z.infer<typeof LogContextSchema>;
