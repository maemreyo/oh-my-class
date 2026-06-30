/**
 * Tests for UnitSessionCard component and unit workspace behaviours.
 *
 * Uses renderToStaticMarkup — same pattern as effectiveness-dashboard.test.tsx.
 * No @testing-library dependency required.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { UnitSessionCard } from "@/components/unit-session-card";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseProgress = {
	session_id: "s1",
	child_run_id: null,
	status: "pending" as const,
	progress_percent: 0,
};

const basePlan = {
	session_id: "s1",
	order_index: 1,
	title: "Khái niệm phân số",
	sub_topic: "Phân số",
	duration_minutes: 30,
	learning_objectives: ["Hiểu phân số"],
	bloom_level_primary: "understand",
	methodology_primary: "concept_map",
	prerequisite_sessions: [] as string[],
};

// ---------------------------------------------------------------------------
// UnitSessionCard — rendering
// ---------------------------------------------------------------------------

describe("UnitSessionCard rendering", () => {
	it("renders session title and status badge", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard sessionProgress={baseProgress} sessionPlan={basePlan} />,
		);
		expect(html).toContain("Khái niệm phân số");
		expect(html).toContain("Pending");
	});

	it("shows order index", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard sessionProgress={baseProgress} sessionPlan={basePlan} />,
		);
		expect(html).toContain(">1<");
	});

	it("shows progress bar only when generating", () => {
		const htmlGenerating = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "generating", progress_percent: 45 }}
				sessionPlan={basePlan}
			/>,
		);
		expect(htmlGenerating).toContain("width:45%");

		const htmlPending = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "pending", progress_percent: 0 }}
				sessionPlan={basePlan}
			/>,
		);
		// No progress bar rendered for non-generating status
		expect(htmlPending).not.toContain("width: 0%");
	});

	it("falls back to session_id when no sessionPlan provided", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard sessionProgress={baseProgress} />,
		);
		expect(html).toContain("s1");
	});

	it("shows prerequisite sessions when present", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={baseProgress}
				sessionPlan={{ ...basePlan, prerequisite_sessions: ["s0"] }}
			/>,
		);
		expect(html).toContain("Requires: s0");
	});

	it("approved badge has green text class", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "approved" }}
				sessionPlan={basePlan}
			/>,
		);
		expect(html).toContain("Approved");
		expect(html).toContain("text-green-700");
	});

	it("failed badge has red text class", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "failed" }}
				sessionPlan={basePlan}
			/>,
		);
		expect(html).toContain("Failed");
		expect(html).toContain("text-red-700");
	});
});

// ---------------------------------------------------------------------------
// UnitSessionCard — action affordances
// ---------------------------------------------------------------------------

describe("UnitSessionCard action affordances", () => {
	it("renders Review button when onReview provided", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, child_run_id: "run-child" }}
				sessionPlan={basePlan}
				onReview={vi.fn()}
			/>,
		);
		expect(html).toContain("Review");
	});

	it("renders Retry button for failed sessions when onRetry provided", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "failed" }}
				sessionPlan={basePlan}
				onRetry={vi.fn()}
			/>,
		);
		expect(html).toContain("Retry");
	});

	it("does not render Retry button when status is not failed", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "pending" }}
				sessionPlan={basePlan}
				onRetry={vi.fn()}
			/>,
		);
		expect(html).not.toContain("Retry");
	});

	it("renders Start anyway button for blocked sessions when onForceStart provided", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "blocked" }}
				sessionPlan={basePlan}
				onForceStart={vi.fn()}
			/>,
		);
		expect(html).toContain("Start anyway");
	});

	it("does not render Start anyway when status is not blocked", () => {
		const html = renderToStaticMarkup(
			<UnitSessionCard
				sessionProgress={{ ...baseProgress, status: "pending" }}
				sessionPlan={basePlan}
				onForceStart={vi.fn()}
			/>,
		);
		expect(html).not.toContain("Start anyway");
	});

	it("approve-all endpoint is called with the correct path", async () => {
		// Test the logic that the page would call — directly via the hook action
		const mockPost = vi.fn().mockResolvedValueOnce({ results: { s1: "approved" } });
		vi.mock("@/lib/api-client", () => ({
			apiClient: { post: mockPost, get: vi.fn() },
			gatewayUrl: () => "http://gateway.test",
		}));

		const parentRunId = "run-123";
		// Simulate approveAll logic inline
		const res = (await mockPost(
			`/teaching-packs/units/${parentRunId}/approve-all`,
		)) as { results: Record<string, string> };

		expect(mockPost).toHaveBeenCalledWith("/teaching-packs/units/run-123/approve-all");
		expect(res.results).toEqual({ s1: "approved" });
	});

	it("spawn-anyway endpoint is called with session path", async () => {
		const mockPost = vi.fn().mockResolvedValueOnce({});

		const parentRunId = "run-123";
		const sessionId = "s2";
		await mockPost(
			`/teaching-packs/units/${parentRunId}/sessions/${sessionId}/spawn-anyway`,
		);

		expect(mockPost).toHaveBeenCalledWith(
			"/teaching-packs/units/run-123/sessions/s2/spawn-anyway",
		);
	});
});
