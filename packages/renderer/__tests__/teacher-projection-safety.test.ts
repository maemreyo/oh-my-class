import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const questionCard = {
	type: "question_card",
	id: "q1",
	text: "Which clue is unsafe?",
	options: { A: "yesterday", B: "often" },
	answer: "A",
	explain: "Finished-time markers require simple past.",
	wrong_reasons: { B: "Often can work with present simple." },
} as const;

describe("teacher projection safety", () => {
	it("preserves answer and rationale fields in answer-key HTML", async () => {
		const html = await renderAgentArtifact({
			artifact_type: "answer_key",
			title: "Teacher-safe question",
			sections: [{ id: "practice", title: "Practice", components: [questionCard] }],
		});

		expect(html).toContain("Finished-time markers require simple past.");
		expect(html).toContain("Often can work with present simple.");
		expect(html).toContain("correct");
	});
});
