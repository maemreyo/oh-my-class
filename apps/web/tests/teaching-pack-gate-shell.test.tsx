import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/hooks/use-teaching-packs", () => ({
	useResumeTeachingPackRun: () => ({
		mutateAsync: vi.fn(),
		isPending: false,
		error: null,
	}),
}));

vi.mock("@/lib/api-client", () => ({
	gatewayUrl: () => "http://gateway.test",
}));

import { TeachingPackGateShell } from "@/components/teaching-packs-gate-shell";

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
});
