import { describe, expect, it } from "vitest";

import { ArtifactSchema, RunSchema } from "./run.js";

describe("RunSchema", () => {
	it("parses the current gateway RunResponse shape", () => {
		const parsed = RunSchema.parse({
			run_id: "run-1",
			status: "running",
			state: { current_step: 1 },
		});

		expect(parsed.run_id).toBe("run-1");
		expect(parsed.state?.current_step).toBe(1);
	});
});

describe("ArtifactSchema", () => {
	it("extends generated artifact content with optional rendered HTML", () => {
		const parsed = ArtifactSchema.parse({
			artifact_type: "lesson",
			theme: "default",
			title: "Fractions intro",
			sections: [{ type: "paragraph", text: "Learn fractions." }],
			rendered_html: "<!DOCTYPE html><html></html>",
		});

		expect(parsed.rendered_html).toContain("DOCTYPE");
	});
});
