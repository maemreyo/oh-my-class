import { describe, expect, it } from "vitest";
import { renderArtifact, renderTemplate } from "../src/renderer.js";

describe("renderer", () => {
	it("renderArtifact throws not-implemented", () => {
		expect(() =>
			renderArtifact({
				artifact_type: "lesson",
				title: "Test Lesson",
				sections: [{}],
			}),
		).toThrow("Not yet implemented");
	});

	it("renderTemplate throws not-implemented", () => {
		expect(() => renderTemplate("base", {})).toThrow("Not yet implemented");
	});
});
