import { describe, expect, it } from "vitest";
import { renderArtifact } from "../src/renderer.js";
import type { ArtifactDataMap, ArtifactType } from "../src/contracts/index.js";

const artifactFixtures = {
	lesson: {
		title: "Accessible Lesson",
		subject: "Math",
		gradeLevel: "Grade 5",
		objectives: ["Explain equivalent fractions"],
		sections: [{ heading: "Warm up", body: "Compare two fraction models." }],
	},
	worksheet: {
		title: "Accessible Worksheet",
		subject: "Math",
		gradeLevel: "Grade 5",
		sections: [{ title: "Practice", questions: [{ id: "w1", prompt: "Draw 1/2", type: "short_answer" }] }],
	},
	quiz: {
		title: "Accessible Quiz",
		subject: "Math",
		gradeLevel: "Grade 5",
		questions: [{ id: "q1", prompt: "Which fraction equals 1/2?", options: [{ label: "A", text: "2/4" }], answer: "SECRET_A11Y_ANSWER" }],
	},
	drill: {
		title: "Accessible Drill",
		subject: "Math",
		gradeLevel: "Grade 5",
		questions: [{ id: "d1", prompt: "Fill the blank: 1/2 = __/4", answer: "SECRET_A11Y_ANSWER", type: "fill" }],
	},
	recap: {
		title: "Accessible Recap",
		subject: "Math",
		gradeLevel: "Grade 5",
		items: [{ id: "r1", concept: "Equivalent fractions", summary: "Different names can show the same amount." }],
	},
	infographic: {
		title: "Accessible Infographic",
		subject: "Math",
		gradeLevel: "Grade 5",
		sections: [{ title: "Fraction bar", content: "Two quarters line up with one half." }],
	},
} satisfies Pick<ArtifactDataMap, "lesson" | "worksheet" | "quiz" | "drill" | "recap" | "infographic">;

describe("artifact accessibility contract", () => {
	for (const [type, data] of Object.entries(artifactFixtures) as ReadonlyArray<[keyof typeof artifactFixtures, ArtifactDataMap[keyof typeof artifactFixtures]]>) {
		it(`renders ${type} with standalone WCAG-critical metadata`, async () => {
			const html = await renderArtifact(type as ArtifactType, { ...data, theme: "high-contrast-dyslexia" } as ArtifactDataMap[ArtifactType]);

			expect(html).toMatch(/<html\s+lang="[^"]+"/);
			expect(html).toMatch(/<meta\s+name="viewport"/);
			expect(html).toContain("oh-my-class");
			expect(html).not.toMatch(/https?:\/\//);
			expect(html).not.toContain("SECRET_A11Y_ANSWER");
		});
	}
});
