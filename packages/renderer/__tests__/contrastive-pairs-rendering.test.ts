import { describe, expect, it } from "vitest";
import { renderAgentArtifact } from "../src/agent-renderer.js";

const contrastivePairsLesson = {
	artifact_type: "lesson",
	theme: "default",
	title: "Contrastive Pairs: Because vs Although",
	metadata: {
		subject: "English",
		grade_level: "Grade 8",
		summary: "Students compare easily confused connector patterns.",
	},
	accessibility: { language: "en" },
	sections: [
		{
			id: "contrastive-pairs",
			title: "Boundary contrast",
			content: "Compare the purpose, examples, non-examples, and boundary notes before choosing a connector.",
			components: [
				{
					type: "contrastive_pairs",
					title: "Because vs Although",
					left_label: "Because: gives the reason",
					right_label: "Although: shows contrast",
					rows: [
						{
							terms: "because / although",
							distinction: "Because points to why something happened; although points to a surprising contrast.",
							example: "Because the rain was heavy, the match was delayed for a long time.",
							non_example: "Although the rain was heavy, the match was delayed for a long time.",
							boundary_note: "If the second clause is expected from the first, use because; if it pushes against the first, use although.",
							teacher_rationale: "TEACHER_ONLY_RATIONALE_TOKEN",
						},
					],
				},
			],
		},
	],
} as const;

describe("Contrastive Pairs rendering", () => {
	it("renders balanced sides, examples, non-examples, and boundary notes without external assets", async () => {
		const html = await renderAgentArtifact(contrastivePairsLesson);

		expect(html).toContain("<!DOCTYPE html>");
		expect(html).toContain("oh-my-class");
		expect(html).not.toMatch(/https?:\/\//);
		expect(html).toContain("contrastive-pairs");
		expect(html).toContain("role=\"region\"");
		expect(html).toContain("Because: gives the reason");
		expect(html).toContain("Although: shows contrast");
		expect(html).toContain("Example");
		expect(html).toContain("Non-example");
		expect(html).toContain("Boundary note");
		expect(html).toContain("overflow-wrap:anywhere");
	});

	it("keeps teacher-only rationales out of student-facing HTML", async () => {
		const html = await renderAgentArtifact(contrastivePairsLesson);

		expect(html).not.toContain("TEACHER_ONLY_RATIONALE_TOKEN");
		expect(html).not.toMatch(/teacher rationale/i);
	});
});
