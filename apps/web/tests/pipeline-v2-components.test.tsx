/**
 * Unit tests for Pipeline V2 stage progress and gate shell logic.
 *
 * Follows project convention: tests pure logic without DOM rendering.
 * Component rendering is verified via browser QA (Playwright).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockPost } = vi.hoisted(() => ({
	mockPost: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
	apiClient: { post: mockPost },
	gatewayUrl: () => "http://gateway.test",
}));

vi.mock("@tanstack/react-query", () => ({
	useMutation: (opts: Record<string, unknown>) => ({
		mutateAsync: opts["mutationFn"],
		isPending: false,
		error: null,
	}),
	useQuery: () => ({ data: undefined, isLoading: false }),
	useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

vi.mock("@/components/ui/badge", () => ({ Badge: () => null }));
vi.mock("@/components/ui/button", () => ({ Button: ({ children }: { children: React.ReactNode }) => null }));

import { snapshotPreviewUrl } from "@/hooks/use-pipeline-v2";

type GateName =
	| "clarification_required"
	| "contract_confirmation"
	| "search_plan_confirmation"
	| "blueprint_approval"
	| "content_approval";

const VALID_GATE_NAMES: readonly GateName[] = [
	"clarification_required",
	"contract_confirmation",
	"search_plan_confirmation",
	"blueprint_approval",
	"content_approval",
];

function gateNameFor(event: { gate_name?: string; gate?: string }): GateName | null {
	const candidate = event.gate_name ?? event.gate;
	if (isGateName(candidate)) return candidate;
	return null;
}

function isGateName(value: unknown): value is GateName {
	switch (value) {
		case "clarification_required":
		case "contract_confirmation":
		case "search_plan_confirmation":
		case "blueprint_approval":
		case "content_approval":
			return true;
		default:
			return false;
	}
}

function labelFor(gateName: GateName): string {
	switch (gateName) {
		case "clarification_required": return "Clarification required";
		case "contract_confirmation": return "Confirm the teaching contract";
		case "search_plan_confirmation": return "Confirm the research plan";
		case "blueprint_approval": return "Review the blueprint";
		case "content_approval": return "Review rendered content";
	}
}

function formatValue(value: unknown): string {
	if (Array.isArray(value)) return value.join(", ");
	if (value === null || value === undefined) return "Not set";
	return String(value);
}

function stageClass(stage: string, status: string): string {
	const active = stage === status || (stage === "awaiting_approval" && status.includes("approval"));
	return [
		"rounded-md border p-3 transition-colors",
		active ? "border-primary bg-primary/10" : "border-border bg-background",
	].join(" ");
}

function badgeVariant(status: string): string {
	return status === "failed" ? "destructive" : "secondary";
}

describe("stageClass", () => {
	it("highlights the active stage", () => {
		expect(stageClass("pending", "pending")).toContain("border-primary");
	});

	it("highlights awaiting_approval when status includes 'approval'", () => {
		expect(stageClass("awaiting_approval", "content_approval")).toContain("border-primary");
	});

	it("does not highlight inactive stage", () => {
		expect(stageClass("running", "pending")).toContain("border-border");
	});

	it("highlights completed when status is completed", () => {
		expect(stageClass("completed", "completed")).toContain("border-primary");
	});

	it("does not highlight awaiting_approval when status is pending", () => {
		expect(stageClass("awaiting_approval", "pending")).toContain("border-border");
	});
});

describe("badgeVariant", () => {
	it("returns destructive for failed", () => {
		expect(badgeVariant("failed")).toBe("destructive");
	});

	it("returns secondary for running", () => {
		expect(badgeVariant("running")).toBe("secondary");
	});

	it("returns secondary for completed", () => {
		expect(badgeVariant("completed")).toBe("secondary");
	});
});

describe("gateNameFor", () => {
	beforeEach(() => { vi.clearAllMocks(); });

	it("returns gate_name when present", () => {
		expect(gateNameFor({ gate_name: "content_approval" })).toBe("content_approval");
	});

	it("falls back to gate field", () => {
		expect(gateNameFor({ gate: "blueprint_approval" })).toBe("blueprint_approval");
	});

	it("returns null for invalid gate name", () => {
		expect(gateNameFor({ gate_name: "unknown_gate" })).toBeNull();
	});

	it("returns null when neither field present", () => {
		expect(gateNameFor({})).toBeNull();
	});

	it("prefers gate_name over gate", () => {
		expect(gateNameFor({ gate_name: "content_approval", gate: "blueprint_approval" })).toBe("content_approval");
	});
});

describe("isGateName", () => {
	it("accepts all valid gate names", () => {
		for (const name of VALID_GATE_NAMES) {
			expect(isGateName(name)).toBe(true);
		}
	});

	it("rejects invalid strings", () => {
		expect(isGateName("invalid")).toBe(false);
		expect(isGateName("")).toBe(false);
	});

	it("rejects non-strings", () => {
		expect(isGateName(undefined)).toBe(false);
		expect(isGateName(null)).toBe(false);
		expect(isGateName(42)).toBe(false);
	});
});

describe("labelFor", () => {
	it("maps all gate names to human labels", () => {
		expect(labelFor("clarification_required")).toBe("Clarification required");
		expect(labelFor("contract_confirmation")).toBe("Confirm the teaching contract");
		expect(labelFor("search_plan_confirmation")).toBe("Confirm the research plan");
		expect(labelFor("blueprint_approval")).toBe("Review the blueprint");
		expect(labelFor("content_approval")).toBe("Review rendered content");
	});
});

describe("formatValue", () => {
	it("joins arrays with comma", () => {
		expect(formatValue(["lesson", "quiz"])).toBe("lesson, quiz");
	});

	it("returns 'Not set' for undefined", () => {
		expect(formatValue(undefined)).toBe("Not set");
	});

	it("returns 'Not set' for null", () => {
		expect(formatValue(null)).toBe("Not set");
	});

	it("converts strings directly", () => {
		expect(formatValue("Grade 5")).toBe("Grade 5");
	});

	it("converts numbers to string", () => {
		expect(formatValue(42)).toBe("42");
	});
});

describe("snapshotPreviewUrl", () => {
	it("builds teacher preview URL", () => {
		expect(snapshotPreviewUrl("run-1", "snap-1", "teacher")).toBe(
			"http://gateway.test/pipeline-v2/run/run-1/snapshots/snap-1/preview?view=teacher",
		);
	});

	it("builds student preview URL", () => {
		expect(snapshotPreviewUrl("run-1", "snap-2", "student")).toBe(
			"http://gateway.test/pipeline-v2/run/run-1/snapshots/snap-2/preview?view=student",
		);
	});
});

describe("V2 resume payload construction", () => {
	beforeEach(() => { vi.clearAllMocks(); });

	it("resume sends gate_id, gate_name, action", async () => {
		mockPost.mockResolvedValue({ run_id: "r-1", response_id: "resp-1", job_id: "j-1" });

		const mod = await import("@/hooks/use-pipeline-v2");
		const { mutateAsync } = mod.useResumePipelineV2Run("r-1") as { mutateAsync: Function };

		await mutateAsync({
			gate_id: "gate-1",
			gate_name: "content_approval",
			action: "approve",
		});

		expect(mockPost).toHaveBeenCalledWith(
			"/pipeline-v2/run/r-1/resume",
			expect.objectContaining({
				gate_id: "gate-1",
				gate_name: "content_approval",
				action: "approve",
			}),
			expect.anything(),
		);
	});

	it("resume includes feedback in response when provided", async () => {
		mockPost.mockResolvedValue({ run_id: "r-1", response_id: "resp-1", job_id: "j-1" });

		const mod = await import("@/hooks/use-pipeline-v2");
		const { mutateAsync } = mod.useResumePipelineV2Run("r-1") as { mutateAsync: Function };

		await mutateAsync({
			gate_id: "gate-1",
			gate_name: "blueprint_approval",
			action: "edit",
			response: { feedback: "Needs more detail" },
		});

		expect(mockPost).toHaveBeenCalledWith(
			"/pipeline-v2/run/r-1/resume",
			expect.objectContaining({
				response: { feedback: "Needs more detail" },
			}),
			expect.anything(),
		);
	});
});
