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

describe("student projection safety", () => {
	it("strips question-card answer and rationale fields from student lesson HTML", async () => {
		const html = await renderAgentArtifact({
			artifact_type: "lesson",
			title: "Student-safe question",
			sections: [{ id: "practice", title: "Practice", components: [questionCard] }],
		});

		expect(html).toContain("Which clue is unsafe?");
		expect(html).not.toContain("Finished-time markers require simple past.");
		expect(html).not.toContain("Often can work with present simple.");
		expect(html).not.toContain("class=\"option correct\"");
		expect(html).not.toContain("<span class=\"plabel\">Giải thích</span>");
	});
});
