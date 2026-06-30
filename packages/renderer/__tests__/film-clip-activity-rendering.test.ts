import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const filmLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Film-based connector lesson",
	metadata: {
		subject: "English",
		grade_level: "Grade 8",
		summary: "Students observe connector use in a short clip context.",
	},
	accessibility: { language: "en" },
	sections: [
		{
			id: "film-activity",
			title: "Film activity",
			content: "Use the clip reference as context only; the export must stay offline-safe.",
			components: [
				{
					type: "film_clip_activity",
					clip_context: "A classroom scene where two students explain why they missed a bus.",
					pre_watch_prompt: "Predict which connector will introduce the reason.",
					while_watch_task: "Listen for because, although, and the sentence after each connector.",
					post_watch_reflection: "Explain which connector matched the speaker's purpose.",
					video_reference: "https://example.com/teacher-reference-only",
					clips: [{ title: "Bus stop scene", description: "Teacher-provided reference only; no embedded media." }],
					hunt_chips: ["because", "although", "reason"],
					post_viewing_note: "Write one reason sentence and one contrast sentence.",
				},
			],
		},
	],
} as const;

describe("Film clip activity rendering", () => {
	it("renders before, during, after, and offline fallback sections", async () => {
		const html = await renderAgentArtifact(filmLesson);

		expect(html).toContain("<!DOCTYPE html>");
		expect(html).toContain("oh-my-class");
		expect(html).toContain("film-clip-activity");
		expect(html).toContain("Before watching");
		expect(html).toContain("While watching");
		expect(html).toContain("After watching");
		expect(html).toContain("Offline reference");
		expect(html).toContain("https://example.com/teacher-reference-only");
		expect(html).toContain("@media print");
	});

	it("does not embed external media, iframes, scripts, or thumbnails", async () => {
		const html = await renderAgentArtifact(filmLesson);

		expect(html).not.toMatch(/<iframe\b/i);
		expect(html).not.toMatch(/<video\b[^>]*\bsrc=/i);
		expect(html).not.toMatch(/<script\b/i);
		expect(html).not.toMatch(/thumbnail/i);
		expect(html).not.toMatch(/src="https?:\/\//i);
	});
});
