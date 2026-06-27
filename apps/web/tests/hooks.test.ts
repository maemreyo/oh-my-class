/**
 * Unit tests for use-run and use-approval hooks.
 *
 * We test the mutationFn / queryFn in isolation by mocking:
 * - @tanstack/react-query  — captures opts and exposes mutationFn/queryFn directly
 * - @/lib/api-client       — records which URL + method was called
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// ── api-client mock ───────────────────────────────────────────────────────────
// vi.hoisted ensures these exist before vi.mock factories run

const { mockPost, mockGet } = vi.hoisted(() => ({
	mockPost: vi.fn(),
	mockGet: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
	apiClient: {
		post: mockPost,
		get: mockGet,
	},
	gatewayUrl: () => "http://gateway.test",
}));

// ── react-query mock: captures mutationFn / queryFn ──────────────────────────

const capturedOpts: { type: string; opts: Record<string, unknown> }[] = [];

vi.mock("@tanstack/react-query", () => ({
	useMutation: (opts: Record<string, unknown>) => {
		capturedOpts.push({ type: "mutation", opts });
		return { mutateAsync: opts["mutationFn"], isPending: false };
	},
	useQuery: (opts: Record<string, unknown>) => {
		capturedOpts.push({ type: "query", opts });
		return { data: undefined, isLoading: false };
	},
	useQueryClient: () => ({
		invalidateQueries: vi.fn(),
	}),
}));

// Imports AFTER mocks so vi.mock() hoisting applies
import { useCreateRun, useRun, useRunStatus } from "@/hooks/use-run";
import { useApproveRun, useRejectRun } from "@/hooks/use-approval";
import {
	snapshotPreviewUrl,
	useCreatePipelineV2Run,
	useResumePipelineV2Run,
} from "@/hooks/use-pipeline-v2";

// ── useCreateRun ──────────────────────────────────────────────────────────────

describe("useCreateRun", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("calls POST /run with request payload", async () => {
		const runData = { run_id: "r-001", status: "created" };
		mockPost.mockResolvedValue(runData);

		const hook = useCreateRun();
		await (hook as { mutateAsync: Function }).mutateAsync({
			raw_request: "Teach photosynthesis",
			class_info: { grade: 5, subject: "science" },
			teacher_id: "t-001",
		});

		expect(mockPost).toHaveBeenCalledWith("/run", {
			raw_request: "Teach photosynthesis",
			class_info: { grade: 5, subject: "science" },
			teacher_id: "t-001",
		});
	});

	it("returns run_id from response", async () => {
		mockPost.mockResolvedValue({ run_id: "r-001", status: "created" });

		const hook = useCreateRun();
		const result = await (hook as { mutateAsync: Function }).mutateAsync({
			raw_request: "Teach math",
			class_info: { grade: 3, subject: "math" },
			teacher_id: "t-001",
		});

		expect(result.run_id).toBe("r-001");
	});
});

// ── useRun ────────────────────────────────────────────────────────────────────

describe("useRun", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("registers query with queryKey [run, runId]", () => {
		useRun("test-123");

		const queryOpts = capturedOpts.find((c) => c.type === "query");
		expect(queryOpts).toBeDefined();
		expect(queryOpts?.opts["queryKey"]).toEqual(["run", "test-123"]);
	});

	it("has enabled: false when runId is null", () => {
		useRun(null);

		const queryOpts = capturedOpts.find((c) => c.type === "query");
		expect(queryOpts?.opts["enabled"]).toBe(false);
	});

	it("queryFn calls GET /run/{runId}", async () => {
		mockGet.mockResolvedValue({ run_id: "test-123", status: "running" });
		useRun("test-123");

		const queryOpts = capturedOpts.find((c) => c.type === "query");
		const result = await (queryOpts?.opts["queryFn"] as () => Promise<unknown>)();

		expect(mockGet).toHaveBeenCalledWith("/run/test-123");
		expect((result as { run_id: string }).run_id).toBe("test-123");
	});

	it("queryFn throws when runId is null", async () => {
		useRun(null);

		const queryOpts = capturedOpts.find((c) => c.type === "query");
		await expect(
			(queryOpts?.opts["queryFn"] as () => Promise<unknown>)(),
		).rejects.toThrow("No run ID");
	});
});

// ── useRunStatus ──────────────────────────────────────────────────────────────

describe("useRunStatus", () => {
	it("returns a subscribe function", () => {
		const { subscribe } = useRunStatus("test-123");
		expect(typeof subscribe).toBe("function");
	});

	it("subscribe returns cleanup function when runId is null", () => {
		const { subscribe } = useRunStatus(null);
		const cleanup = subscribe(() => {});
		expect(typeof cleanup).toBe("function");
		expect(() => cleanup()).not.toThrow();
	});
});

// ── useApproveRun ─────────────────────────────────────────────────────────────

describe("useApproveRun", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("calls POST /run/{runId}/approve for approve action", async () => {
		mockPost.mockResolvedValue({ status: "resumed", message: "ok", run_id: "r-001" });

		const hook = useApproveRun("r-001");
		await (hook as { mutateAsync: Function }).mutateAsync({ action: "approve" });

		expect(mockPost).toHaveBeenCalledWith("/run/r-001/approve", {
			action: "approve",
		});
	});

	it("calls POST /run/{runId}/reject for reject action", async () => {
		mockPost.mockResolvedValue({ status: "resumed", message: "ok", run_id: "r-001" });

		const hook = useApproveRun("r-001");
		await (hook as { mutateAsync: Function }).mutateAsync({
			action: "reject",
			feedback: "Too short",
		});

		expect(mockPost).toHaveBeenCalledWith("/run/r-001/reject", {
			action: "reject",
			feedback: "Too short",
		});
	});
});

// ── useRejectRun ──────────────────────────────────────────────────────────────

describe("useRejectRun", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("calls POST /run/{runId}/reject with feedback", async () => {
		mockPost.mockResolvedValue({ status: "resumed", message: "ok", run_id: "r-001" });

		const hook = useRejectRun("r-001");
		await (hook as { mutateAsync: Function }).mutateAsync({
			feedback: "Needs more examples",
		});

		expect(mockPost).toHaveBeenCalledWith("/run/r-001/reject", {
			action: "reject",
			feedback: "Needs more examples",
		});
	});

	it("always sends action: reject", async () => {
		mockPost.mockResolvedValue({ status: "resumed", message: "ok", run_id: "r-001" });

		const hook = useRejectRun("r-001");
		await (hook as { mutateAsync: Function }).mutateAsync({ feedback: "Too short" });

		const callArgs = mockPost.mock.calls[0][1] as Record<string, unknown>;
		expect(callArgs["action"]).toBe("reject");
	});
});

describe("useCreatePipelineV2Run", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("calls POST /pipeline-v2/run with an idempotency key", async () => {
		mockPost.mockResolvedValue({ run_id: "run-v2", job_id: "job-v2", status: "pending" });

		const hook = useCreatePipelineV2Run();
		await (hook as { mutateAsync: Function }).mutateAsync({
			raw_request: "Teach fractions",
			class_info: { grade: 5, subject: "math" },
		});

		expect(mockPost).toHaveBeenCalledWith(
			"/pipeline-v2/run",
			{ raw_request: "Teach fractions", class_info: { grade: 5, subject: "math" } },
			expect.objectContaining({
				headers: expect.objectContaining({ "Idempotency-Key": expect.stringContaining("create:") }),
			}),
		);
	});
});

describe("useResumePipelineV2Run", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		capturedOpts.length = 0;
	});

	it("calls generic V2 resume endpoint", async () => {
		mockPost.mockResolvedValue({ run_id: "run-v2", response_id: "resp-1", job_id: "job-1" });

		const hook = useResumePipelineV2Run("run-v2");
		await (hook as { mutateAsync: Function }).mutateAsync({
			gate_id: "gate-1",
			gate_name: "contract_confirmation",
			action: "approve",
			response: { feedback: "Looks good" },
		});

		expect(mockPost).toHaveBeenCalledWith(
			"/pipeline-v2/run/run-v2/resume",
			{
				gate_id: "gate-1",
				gate_name: "contract_confirmation",
				action: "approve",
				response: { feedback: "Looks good" },
			},
			expect.objectContaining({
				headers: expect.objectContaining({ "Idempotency-Key": expect.stringContaining("resume:run-v2") }),
			}),
		);
	});
});

describe("snapshotPreviewUrl", () => {
	it("builds the V2 rendered preview URL", () => {
		expect(snapshotPreviewUrl("run-v2", "snap-1", "teacher")).toBe(
			"http://gateway.test/pipeline-v2/run/run-v2/snapshots/snap-1/preview?view=teacher",
		);
	});

	it("builds student preview URL", () => {
		expect(snapshotPreviewUrl("run-v2", "snap-2", "student")).toBe(
			"http://gateway.test/pipeline-v2/run/run-v2/snapshots/snap-2/preview?view=student",
		);
	});
});
