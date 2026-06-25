import { z } from "zod";
import { ArtifactContentSchema } from "./generated/artifact.js";

// Matches gateway RunResponse (runs.py) plus extended fields added as pipeline matures
export const RunSchema = z.object({
	run_id: z.string(),
	status: z.string(),
	topic: z.string().optional(),
	current_step: z.number().int().optional(),
	artifact_types: z.array(z.string()).optional(),
	state: z.record(z.string(), z.unknown()).optional(),
});

export type Run = z.infer<typeof RunSchema>;

// ArtifactContent + rendered_html produced by the renderer
export const ArtifactSchema = ArtifactContentSchema.extend({
	rendered_html: z.string().optional(),
});

export type Artifact = z.infer<typeof ArtifactSchema>;
