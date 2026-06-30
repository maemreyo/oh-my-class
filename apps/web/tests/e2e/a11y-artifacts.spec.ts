import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "@playwright/test";
import { renderArtifact, type ArtifactDataMap, type ArtifactType } from "@oh-my-class/renderer";

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

test.describe("rendered artifact accessibility", () => {
	test.setTimeout(90_000);

	for (const [type, data] of Object.entries(artifactFixtures) as ReadonlyArray<[keyof typeof artifactFixtures, ArtifactDataMap[keyof typeof artifactFixtures]]>) {
		test(`${type} has no WCAG 2.1 AA axe violations`, async ({ page }) => {
			const html = await renderArtifact(type as ArtifactType, { ...data, theme: "high-contrast-dyslexia" } as ArtifactDataMap[ArtifactType]);
			await page.setContent(html, { waitUntil: "domcontentloaded" });

			const results = await new AxeBuilder({ page })
				.withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
				.analyze();

			expect(results.violations).toEqual([]);
		});
	}
});
