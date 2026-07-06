import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/api-client", () => ({
	gatewayUrl: () => "http://gateway.test",
}));

vi.mock("@/components/ui/button", () => ({
	Button: ({ children }: { readonly children: React.ReactNode }) => <button type="button">{children}</button>,
}));

import { TeachingPackGateBody } from "@/components/teaching-packs-gate-bodies";
import { strategyBlueprintEvent } from "./teaching-pack-strategy-fixtures";

describe("TeachingPackGateBody structured summaries", () => {
	it("renders search plan details without making raw JSON the primary view", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="search_plan_confirmation"
				event={{
					query_plan: {
						reason: "Curriculum is ambiguous",
						estimated_work: "3 sources",
						budget: "standard",
						queries: ["Grade 5 fractions misconception", "Vietnam CT 2018 fractions"],
					},
				}}
			/>,
		);

		expect(html).toContain("Research plan");
		expect(html).toContain("Curriculum is ambiguous");
		expect(html).toContain("Grade 5 fractions misconception");
		expect(html).not.toContain("&quot;query_plan&quot;");
	});

	it("renders blueprint fields and learning objectives as teacher-readable sections", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="blueprint_approval"
				event={{
					blueprint: {
						topic: "Fractions",
						grade_level: "Grade 5",
						subject: "Math",
						duration_minutes: 45,
						learning_objectives: [
							{ objective: "Compare fractions", bloom_level: "understand" },
						],
						assessment_checkpoints: [{ checkpoint: "Exit ticket", timing: "end" }],
					},
				}}
			/>,
		);

		expect(html).toContain("Blueprint summary");
		expect(html).toContain("Fractions");
		expect(html).toContain("Learning objectives");
		expect(html).toContain("Compare fractions");
		expect(html).toContain("Assessment checkpoints");
		expect(html).not.toContain("&quot;learning_objectives&quot;");
	});

	it("hides teaching strategy for old blueprint gate payloads", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="blueprint_approval"
				event={{ blueprint: { topic: "Fractions", grade_level: "Grade 5" } }}
			/>,
		);

		expect(html).toContain("Blueprint summary");
		expect(html).not.toContain("Teaching strategy");
	});

	it("renders finalized teaching strategy with compact summary and details", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="blueprint_approval"
				event={strategyBlueprintEvent()}
			/>,
		);

		expect(html).toContain("Teaching strategy");
		expect(html).toContain("Contrastive fractions");
		expect(html).toContain("Strong fit");
		expect(html).toContain("contrastive pairs");
		expect(html).toContain("vocab cluster");
		expect(html).toContain("View strategy details");
		expect(html).toContain("Artifact projections");
		expect(html).toContain("Student-facing and teacher-only split");
		expect(html).not.toContain("0.91");
	});

	it("renders variants and fallback profiles as notes", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="blueprint_approval"
				event={strategyBlueprintEvent()}
			/>,
		);

		expect(html).toContain("Practice-first fractions");
		expect(html).toContain("Fallback note");
		expect(html).toContain("Interactive number line is replaced");
		expect(html).not.toContain("Fallback drill</span>");
	});

	it("renders artifact workflow progress in content approval", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-1"
				gateName="content_approval"
				event={{
					snapshot_ids: ["snapshot-lesson"],
					artifacts: [
						{
							artifact_id: "lesson-1",
							artifact_type: "lesson",
							status: "ready",
						},
					],
				}}
			/>,
		);

		expect(html).toContain("Artifact status");
		expect(html).toContain("lesson-1");
		expect(html).toContain("Ready");
		expect(html).toContain("Student view");
	});
});
