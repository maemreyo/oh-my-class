import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const conceptMapLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Concept Map Fractions",
	metadata: {
		subject: "Math",
		grade_level: "Grade 5",
		summary: "A concept-map lesson for grouping fraction terms.",
	},
	accessibility: { language: "en" },
	sections: [
		{
			id: "concept-map",
			title: "Relationship map",
			content: "Group related vocabulary and explain the connection.",
			components: [
				{
					type: "vocab_cluster",
					title: "Equivalent fraction cluster",
					description: "Relationships: value, model, and simplification",
					items: [
						{ word: "equivalent", definition: "same value", example: "1/2 and 2/4" },
						{ word: "numerator", definition: "top number", example: "the 2 in 2/4" },
						{ word: "denominator", definition: "bottom number", example: "the 4 in 2/4" },
						{ word: "simplify", definition: "rename with smaller equal parts", example: "2/4 becomes 1/2" },
					],
					discrimination_prompt: "Navigate from model to value before choosing a rule.",
				},
			],
		},
	],
} as const;

describe("Concept Map vocab cluster rendering", () => {
	it("renders nodes, groups, relationships, and print-safe standalone HTML", async () => {
		const html = await renderAgentArtifact(conceptMapLesson);

		expect(html).toContain("<!DOCTYPE html>");
		expect(html).toContain("oh-my-class");
		expect(html).not.toMatch(/https?:\/\//);
		expect(html).toContain("@media print");
		expect(html).toContain("vocab-cluster");
		expect(html).toContain("aria-label=\"Concept Map vocabulary cluster\"");
		expect(html).toContain("Equivalent fraction cluster");
		expect(html).toContain("equivalent");
		expect(html).toContain("same value");
		expect(html).toContain("Relationships: value, model, and simplification");
		expect(html).toContain("Navigate from model to value");
	});
});
