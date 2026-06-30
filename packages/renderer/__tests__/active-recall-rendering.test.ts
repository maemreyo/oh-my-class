import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const activeRecallLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Active recall fraction check",
	metadata: {
		subject: "Math",
		grade_level: "Grade 5",
		summary: "Students retrieve before seeing the explanation.",
	},
	accessibility: { language: "en" },
	sections: [
		{
			id: "recall",
			title: "Retrieve first",
			content: "Students answer from memory before opening the reveal.",
			components: [
				{
					type: "active_recall_prompt",
					instruction: "Without notes, write two fractions equivalent to 1/2.",
					time_minutes: 3,
					scaffold_hint: "Think about multiplying both numerator and denominator by the same number.",
					reveal_answer: "2/4 and 3/6 are equivalent to 1/2.",
					teacher_rationale: "TEACHER_ONLY_RATIONALE_TOKEN",
					reflection_note: "Circle your confidence, then write what helped you remember.",
				},
			],
		},
	],
} as const;

describe("Active Recall prompt rendering", () => {
	it("renders prompt, reveal area, confidence check, and reflection note", async () => {
		const html = await renderAgentArtifact(activeRecallLesson);

		expect(html).toContain("<!DOCTYPE html>");
		expect(html).toContain("oh-my-class");
		expect(html).toContain("active-recall-prompt");
		expect(html).toContain("Without notes, write two fractions equivalent to 1/2.");
		expect(html).toContain("Show recall answer");
		expect(html).toContain("Confidence check");
		expect(html).toContain("Still learning");
		expect(html).toContain("Confident");
		expect(html).toContain("Circle your confidence");
	});

	it("supports reduced-motion instant reveal and keyboard button semantics", async () => {
		const html = await renderAgentArtifact(activeRecallLesson);

		expect(html).toContain("@media (prefers-reduced-motion: reduce)");
		expect(html).toContain("<button");
		expect(html).toContain("aria-controls");
		expect(html).toContain("aria-expanded=\"false\"");
		expect(html).not.toContain("requires-animation");
	});

	it("keeps teacher rationale out of initial student-facing print", async () => {
		const html = await renderAgentArtifact(activeRecallLesson);

		expect(html).not.toContain("TEACHER_ONLY_RATIONALE_TOKEN");
		expect(html).not.toMatch(/teacher rationale/i);
		expect(html).toContain("student-print-first");
	});
});
