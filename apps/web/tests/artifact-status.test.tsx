import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/api-client", () => ({
	gatewayUrl: () => "http://gateway.test",
}));

import { TeachingPackGateBody } from "@/components/teaching-packs-gate-bodies";
import { gateEventWithRunArtifactStatuses } from "@/app/(dashboard)/runs/[runId]/page";

describe("teacher-facing artifact status", () => {
	it("uses run-level artifact statuses when a gate event does not include them", () => {
		const event = gateEventWithRunArtifactStatuses(
			{
				gate_id: "gate-content",
				gate_name: "content_approval",
				snapshot_ids: [],
			},
			[
				{
					artifact_id: "quiz-1",
					artifact_type: "quiz",
					status: "failed",
					summary: "Could not safely generate the quiz.",
					teacher_action: "Request edits to regenerate this artifact.",
				},
			],
		);

		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-status"
				gateName="content_approval"
				event={event}
			/>,
		);

		expect(html).toContain("Artifact status");
		expect(html).toContain("Failed");
		expect(html).toContain("Request edits to regenerate this artifact.");
	});

	it("renders failed, skipped, regenerating, and escalated states with teacher actions", () => {
		const html = renderToStaticMarkup(
			<TeachingPackGateBody
				runId="run-status"
				gateName="content_approval"
				event={{
					artifact_statuses: [
						{
							artifact_id: "lesson-1",
							artifact_type: "lesson",
							status: "passed",
							summary: "Generated and ready for teacher review.",
							teacher_action: "Review the generated artifact.",
						},
						{
							artifact_id: "quiz-1",
							artifact_type: "quiz",
							status: "failed",
							summary: "Artifact generation failed. Request edits to regenerate this item.",
							teacher_action: "Request edits to regenerate this artifact.",
						},
						{
							artifact_id: "recap",
							artifact_type: "recap",
							status: "skipped_due_dependency",
							summary: "Skipped because a required earlier artifact failed.",
							teacher_action: "Fix the failed dependency, then regenerate.",
						},
						{
							artifact_id: "drill",
							artifact_type: "drill",
							status: "regenerating",
							summary: "Generation is still in progress.",
							teacher_action: "Wait for this artifact to finish generating.",
						},
						{
							artifact_id: "worksheet",
							artifact_type: "worksheet",
							status: "escalated",
							summary: "Escalated for operator review.",
							teacher_action: "Wait for operator review or contact support.",
						},
					],
				}}
			/>,
		);

		expect(html).toContain("Artifact status");
		expect(html).toContain("Passed");
		expect(html).toContain("Failed");
		expect(html).toContain("Skipped due dependency");
		expect(html).toContain("Regenerating");
		expect(html).toContain("Escalated");
		expect(html).toContain("Request edits to regenerate this artifact.");
		expect(html).not.toContain("Traceback");
	});
});
