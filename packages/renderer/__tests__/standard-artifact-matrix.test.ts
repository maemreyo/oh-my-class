import { describe, expect, it } from "vitest";
import { renderArtifact } from "../src/renderer.js";
import type { ArtifactDataMap, ArtifactType } from "../src/contracts/index.js";

const themes = ["default", "ocean", "forest"] as const;

const standardArtifacts = {
	lesson: {
		title: "Standard Lesson",
		subject: "Math",
		gradeLevel: "Grade 5",
		objectives: ["Explain equivalent fractions"],
		sections: [{ heading: "Warm up", body: "Compare two fraction models." }],
	},
	worksheet: {
		title: "Standard Worksheet",
		subject: "Math",
		gradeLevel: "Grade 5",
		sections: [{ title: "Practice", questions: [{ id: "w1", prompt: "Draw 1/2", type: "short_answer" }] }],
	},
	quiz: {
		title: "Standard Quiz",
		subject: "Math",
		gradeLevel: "Grade 5",
		questions: [{ id: "q1", prompt: "Which fraction equals 1/2?", options: [{ label: "A", text: "2/4" }], answer: "SECRET_STANDARD_ANSWER", explain: "SECRET_STANDARD_EXPLANATION" }],
	},
	drill: {
		title: "Standard Drill",
		subject: "Math",
		gradeLevel: "Grade 5",
		questions: [{ id: "d1", prompt: "Fill the blank: 1/2 = __/4", answer: "SECRET_STANDARD_ANSWER", type: "fill" }],
	},
	recap: {
		title: "Standard Recap",
		subject: "Math",
		gradeLevel: "Grade 5",
		items: [{ id: "r1", concept: "Equivalent fractions", summary: "Different names can show the same amount." }],
	},
	infographic: {
		title: "Standard Infographic",
		subject: "Math",
		gradeLevel: "Grade 5",
		sections: [{ title: "Fraction bar", content: "Two quarters line up with one half." }],
	},
} satisfies Pick<ArtifactDataMap, "lesson" | "worksheet" | "quiz" | "drill" | "recap" | "infographic">;

describe("standard artifact renderer matrix", () => {
	for (const [type, data] of Object.entries(standardArtifacts) as ReadonlyArray<[keyof typeof standardArtifacts, ArtifactDataMap[keyof typeof standardArtifacts]]>) {
		for (const theme of themes) {
			it(`renders ${type} with ${theme} as standalone student-safe HTML`, async () => {
				const html = await renderArtifact(type as ArtifactType, { ...data, theme } as ArtifactDataMap[ArtifactType]);

				expect(html).toContain("<!DOCTYPE html>");
				expect(html).toContain("viewport");
				expect(html).toContain("oh-my-class");
				expect(html).toContain("@media print");
				expect(html).not.toMatch(/https?:\/\//);
				expect(html).not.toContain("SECRET_STANDARD_ANSWER");
				expect(html).not.toContain("SECRET_STANDARD_EXPLANATION");
			});
		}
	}
});
