import { describe, expect, it } from "vitest";
import { UnknownContentComponentError, isContentComponent, renderAgentArtifact } from "../src/agent-renderer.js";

describe("renderer component strictness", () => {
	it("rejects unknown components with section context", async () => {
		const artifact = {
			artifact_type: "lesson",
			title: "Strict components",
			sections: [
				{
					id: "source-section",
					title: "Source",
					components: [{ type: "unknown_component" }],
				},
			],
		};

		await expect(renderAgentArtifact(artifact)).rejects.toThrow(UnknownContentComponentError);
		await expect(renderAgentArtifact(artifact)).rejects.toThrow("unknown_component");
		await expect(renderAgentArtifact(artifact)).rejects.toThrow("source-section");
	});

	it("accepts only registered component types", () => {
		expect(isContentComponent({ type: "question_card", id: "q1", text: "Q", options: {}, answer: "A", explain: "Because" })).toBe(true);
		expect(isContentComponent({ type: "unknown_component" })).toBe(false);
		expect(isContentComponent({ type: "" })).toBe(false);
	});

	it("rejects random object components with type strings", () => {
		for (const index of Array.from({ length: 20 }, (_, itemIndex) => itemIndex)) {
			expect(isContentComponent({ type: `random_${index}`, value: index })).toBe(false);
		}
	});
});
