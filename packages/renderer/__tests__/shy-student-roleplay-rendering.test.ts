import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const roleplayLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Quiet 1:1 roleplay practice",
	metadata: {
		subject: "English",
		grade_level: "Grade 6",
		summary: "A low-pressure roleplay for a shy student.",
	},
	accessibility: { language: "en" },
	sections: [
		{
			id: "roleplay",
			title: "Private practice card",
			content: "Practice softly with a partner or teacher before sharing anything publicly.",
			components: [
				{
					type: "roleplay_script",
					instruction: "Try one line at a time. You may point, whisper, or read from the card.",
					confidence_scaffold: "You can pause, ask for a hint, or repeat after the teacher.",
					coaching_notes: ["TEACHER_ONLY_COACHING_TOKEN"],
					lines: [
						{ speaker: "Teacher", speaker_class: "teacher", text: "I can help you start: I feel [blank_1] today.", cue: "Offer a choice card before asking for speech." },
						{ speaker: "Student", speaker_class: "student", text: "I feel calm today.", cue: "Student can point first, then read if ready." },
					],
					answer_key: ["calm"],
				},
			],
		},
	],
} as const;

describe("Shy Student 1:1 roleplay rendering", () => {
	it("renders teacher/student labels, cues, and confidence scaffold with print cards", async () => {
		const html = await renderAgentArtifact(roleplayLesson);

		expect(html).toContain("<!DOCTYPE html>");
		expect(html).toContain("oh-my-class");
		expect(html).toContain("roleplay-card");
		expect(html).toContain("page-break-inside: avoid");
		expect(html).toContain("Teacher");
		expect(html).toContain("Student");
		expect(html).toContain("Cue");
		expect(html).toContain("You can pause, ask for a hint");
		expect(html).toContain("You may point, whisper, or read from the card.");
	});

	it("keeps teacher-only coaching and answers out of student-facing scripts", async () => {
		const html = await renderAgentArtifact(roleplayLesson);

		expect(html).not.toContain("TEACHER_ONLY_COACHING_TOKEN");
		expect(html).not.toMatch(/Đáp án|Answer key|teacher-only coaching/i);
	});

	it("keeps the fixture tone supportive and avoids public-performance pressure", async () => {
		const html = await renderAgentArtifact(roleplayLesson);

		expect(html).toContain("partner or teacher");
		expect(html).not.toMatch(/perform in front of the class|speak loudly|everyone is watching|don't be shy/i);
	});
});
