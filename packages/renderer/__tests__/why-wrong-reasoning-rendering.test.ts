import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const questionComponent = {
	type: "question_card",
	id: "q1",
	text: "Which sentence uses although correctly?",
	options: {
		A: "Although it rained, we played inside.",
		B: "Although because it rained, we stayed home.",
		C: "We stayed home although because it rained.",
	},
	answer: "A",
	explain: "Although introduces a contrast between two ideas.",
	wrong_reasons: {
		B: "B stacks two connectors and makes the clause relationship unclear.",
		C: "C puts although before a reason phrase instead of a contrast clause.",
	},
} as const;

const studentLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Why wrong reasoning check",
	metadata: { subject: "English", grade_level: "Grade 7" },
	accessibility: { language: "en" },
	sections: [{ id: "practice", title: "Practice", content: "Choose first.", components: [questionComponent] }],
} as const;

const teacherAnswerKey = {
	artifact_type: "answer_key",
	theme: "default",
	title: "Why wrong reasoning key",
	accessibility: { language: "en" },
	sections: [{ id: "practice", title: "Practice", components: [questionComponent] }],
} as const;

describe("Why Wrong Reasoning rendering", () => {
	it("keeps wrong reasons out of initial student-facing lesson HTML", async () => {
		const html = await renderAgentArtifact(studentLesson);

		expect(html).toContain("Which sentence uses although correctly?");
		expect(html).not.toContain("B stacks two connectors");
		expect(html).not.toContain("C puts although before");
		expect(html).not.toContain("wrong-section");
	});

	it("groups wrong reasons by question and distractor in teacher answer-key output", async () => {
		const html = await renderAgentArtifact(teacherAnswerKey);

		expect(html).toContain("q-q1");
		expect(html).toContain("Phân tích lựa chọn chưa phù hợp");
		expect(html).toContain("B stacks two connectors");
		expect(html).toContain("C puts although before");
		expect(html).toContain("aria-live=\"polite\"");
	});
});
