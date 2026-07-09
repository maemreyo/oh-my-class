import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { strategyFeedbackResponse } from "@/components/teaching-packs-gate-shell-utils";

vi.mock("@/hooks/use-teaching-packs", () => ({
	useResumeTeachingPackRun: () => ({
		mutateAsync: vi.fn(),
		isPending: false,
		error: null,
	}),
	useRequestArtifactRevision: () => ({
		mutate: vi.fn(),
		isPending: false,
		error: null,
	}),
	useTranslateSlideDeck: () => ({
		mutateAsync: vi.fn(),
		isPending: false,
		error: null,
	}),
}));

vi.mock("@/lib/api-client", () => ({
	gatewayUrl: () => "http://gateway.test",
}));

import { TeachingPackGateShell } from "@/components/teaching-packs-gate-shell";
import { strategyBlueprintEvent } from "./teaching-pack-strategy-fixtures";

describe("TeachingPackGateShell", () => {
	it("shows scoped rejection when content approval only has artifact statuses", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateShell
				runId="run-status"
				event={{
					gate_id: "gate-content",
					gate_name: "content_approval",
					artifact_statuses: [
						{
							artifact_id: "quiz-1",
							artifact_type: "quiz",
							status: "failed",
							summary: "Could not safely generate the quiz.",
							teacher_action: "Request edits to regenerate this artifact.",
						},
					],
				}}
			/>,
		);

		expect(html).toContain("Reject specific artifacts");
	});

	 it("shows structured section editor when content artifacts include sections", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateShell
				runId="run-editor"
				event={{
					gate_id: "gate-content",
					gate_name: "content_approval",
					content_artifacts: [
						{
							artifact_id: "lesson-1",
							artifact_type: "lesson",
							sections: [
								{
									section_id: "warmup",
									title: "Warm-up",
									content: "Compare two equivalent fractions.",
								},
							],
						},
					],
				}}
			/>,
		);

		expect(html).toContain("Edit a section");
	});

	it("shows explainable approval evidence and fast-lane affordances", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateShell
				runId="run-trust"
					event={{
					gate_id: "gate-content",
					gate_name: "content_approval",
					auto_approved: true,
					trust_score: 0.82,
					revert_window_seconds: 900,
					artifact_explanations: [
						{
							artifact_id: "quiz-1",
							artifact_type: "quiz",
							judge_rationale: "Quiz aligns to the objectives.",
							revision_count: 2,
							healing_history: [{ strategy: "rewrite", note: "Fixed missing rubric." }],
							approval_mode: "auto_approved",
						},
					],
				}}
			/>,
		);

		expect(html).toContain("Auto-approved fast lane");
		expect(html).toContain("View details");
		expect(html).toContain("Revert available for 15 minutes");
		expect(html).toContain("Teacher trust score");
		expect(html).toContain("82%");
		expect(html).toContain("Quiz aligns to the objectives.");
		expect(html).toContain("Healing history");
		expect(html).toContain("rewrite: Fixed missing rubric.");
	});

	it("shows bounded strategy feedback controls on blueprint approval", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateShell
				runId="run-strategy"
				event={{
					gate_id: "gate-blueprint",
					gate_name: "blueprint_approval",
					...strategyBlueprintEvent(),
				}}
			/>,
		);

		expect(html).toContain("Bounded strategy feedback");
		expect(html).toContain("More practice");
		expect(html).toContain("Lower teacher load");
		expect(html).toContain("Exact component placement stays engine-owned");
	});

	it("maps strategy feedback to typed resume payload", () => {
		const response = strategyFeedbackResponse({
			event_type: "request_more_practice",
			value: "vocab_cluster",
			rationale: "Need more scaffolded repetition",
		});

		expect(response).toEqual({
			component_strategy_feedback: {
				event_type: "request_more_practice",
				source: "teacher",
				value: "vocab_cluster",
				rationale: "Need more scaffolded repetition",
			},
		});
	});
});
