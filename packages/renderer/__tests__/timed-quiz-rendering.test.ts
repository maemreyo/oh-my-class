import { describe, expect, it } from "vitest";
import { renderArtifact } from "../src/renderer.js";

describe("Timed Quiz rendering", () => {
	it("renders print-safe timing badges for quiz items without external timer scripts", async () => {
		const html = await renderArtifact("quiz", {
			title: "Timed connector quiz",
			subject: "English",
			gradeLevel: "Grade 7",
			timeLimit: 8,
			questions: [
				{ id: "q1", prompt: "Choose the contrast connector.", options: [{ label: "A", text: "although" }], answer: "A", timeMinutes: 2 },
				{ id: "q2", prompt: "Choose the reason connector.", options: [{ label: "A", text: "because" }], answer: "A", timeMinutes: 3 },
			],
		});

		expect(html).toContain("timed-quiz-summary");
		expect(html).toContain("Suggested total time");
		expect(html).toContain("time-badge");
		expect(html).toContain("Suggested time: 2 minutes");
		expect(html).toContain("Print note: use the badge as pacing guidance");
		expect(html).not.toContain("<script");
		expect(html).not.toMatch(/https?:\/\//);
	});

	it("renders timing metadata for drill items as readable copy", async () => {
		const html = await renderArtifact("drill", {
			title: "Timed fluency drill",
			subject: "Math",
			gradeLevel: "Grade 5",
			timeLimit: 6,
			questions: [
				{ id: "d1", prompt: "1/2 = __/4", answer: "2", type: "fill", timeMinutes: 1 },
			],
		});

		expect(html).toContain("timed-quiz-summary");
		expect(html).toContain("Suggested time: 1 minute");
		expect(html).toContain("aria-label=\"Suggested time for item d1\"");
		expect(html).not.toContain("countdown");
		expect(html).not.toContain("<script");
	});
});
