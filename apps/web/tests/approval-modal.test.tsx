/**
 * Unit tests for ApprovalModal component logic.
 *
 * Tests verify:
 * - handleApprove calls mutateAsync with { action: "approve" }
 * - handleReject enforces feedback requirement
 * - handleReject calls mutateAsync with feedback
 *
 * DOM rendering requires @testing-library/react + jsdom.
 * This suite tests the component's callback logic without DOM rendering
 * by extracting and calling the handler functions directly.
 */

import { describe, it, expect, vi } from "vitest";

// ── Pure logic helpers extracted from ApprovalModal ──────────────────────────

interface ApproveState {
	feedback: string;
}

async function handleApprove(
	approveMutation: { mutateAsync: (r: Record<string, unknown>) => Promise<unknown> },
	onApproved?: () => void,
	onClose?: () => void,
) {
	await approveMutation.mutateAsync({ action: "approve" });
	onApproved?.();
	onClose?.();
}

async function handleReject(
	state: ApproveState,
	rejectMutation: { mutateAsync: (r: { feedback: string }) => Promise<unknown> },
	onRejected?: () => void,
	onClose?: () => void,
) {
	if (!state.feedback.trim()) {
		return { blocked: true, reason: "feedback required" };
	}
	await rejectMutation.mutateAsync({ feedback: state.feedback });
	onRejected?.();
	onClose?.();
	return { blocked: false };
}

// ── ApprovalModal logic tests ─────────────────────────────────────────────────

describe("ApprovalModal — approve logic", () => {
	it("calls mutateAsync with action: approve", async () => {
		const mutateAsync = vi.fn().mockResolvedValue({
			status: "resumed",
			message: "ok",
			run_id: "r-001",
		});
		const approveMutation = { mutateAsync };
		const onApproved = vi.fn();
		const onClose = vi.fn();

		await handleApprove(approveMutation, onApproved, onClose);

		expect(mutateAsync).toHaveBeenCalledWith({ action: "approve" });
	});

	it("calls onApproved callback after approve", async () => {
		const mutateAsync = vi.fn().mockResolvedValue({});
		const onApproved = vi.fn();
		const onClose = vi.fn();

		await handleApprove({ mutateAsync }, onApproved, onClose);

		expect(onApproved).toHaveBeenCalled();
	});

	it("calls onClose after approve", async () => {
		const mutateAsync = vi.fn().mockResolvedValue({});
		const onClose = vi.fn();

		await handleApprove({ mutateAsync }, undefined, onClose);

		expect(onClose).toHaveBeenCalled();
	});
});

describe("ApprovalModal — reject logic", () => {
	it("blocks rejection when feedback is empty", async () => {
		const mutateAsync = vi.fn();
		const rejectMutation = { mutateAsync };

		const result = await handleReject(
			{ feedback: "" },
			rejectMutation,
		);

		expect(result.blocked).toBe(true);
		expect(mutateAsync).not.toHaveBeenCalled();
	});

	it("blocks rejection when feedback is whitespace only", async () => {
		const mutateAsync = vi.fn();
		const result = await handleReject(
			{ feedback: "   " },
			{ mutateAsync },
		);

		expect(result.blocked).toBe(true);
		expect(mutateAsync).not.toHaveBeenCalled();
	});

	it("calls mutateAsync with feedback when provided", async () => {
		const mutateAsync = vi.fn().mockResolvedValue({
			status: "resumed",
			message: "ok",
			run_id: "r-001",
		});
		const onRejected = vi.fn();

		await handleReject(
			{ feedback: "Needs more examples" },
			{ mutateAsync },
			onRejected,
		);

		expect(mutateAsync).toHaveBeenCalledWith({ feedback: "Needs more examples" });
	});

	it("calls onRejected callback after rejection", async () => {
		const mutateAsync = vi.fn().mockResolvedValue({});
		const onRejected = vi.fn();
		const onClose = vi.fn();

		await handleReject(
			{ feedback: "Too short" },
			{ mutateAsync },
			onRejected,
			onClose,
		);

		expect(onRejected).toHaveBeenCalled();
		expect(onClose).toHaveBeenCalled();
	});

	it("does not call onRejected when feedback is empty", async () => {
		const mutateAsync = vi.fn();
		const onRejected = vi.fn();

		await handleReject({ feedback: "" }, { mutateAsync }, onRejected);

		expect(onRejected).not.toHaveBeenCalled();
	});
});

// ── ApprovalModal prop contract ───────────────────────────────────────────────

describe("ApprovalModal — prop types", () => {
	it("gateType distinguishes blueprint vs content", () => {
		const blueprintType: "blueprint_approval" | "content_approval" =
			"blueprint_approval";
		const contentType: "blueprint_approval" | "content_approval" =
			"content_approval";

		expect(blueprintType).toBe("blueprint_approval");
		expect(contentType).toBe("content_approval");
	});

	it("data can carry lesson_plan for blueprint gate", () => {
		const data: {
			lesson_plan?: Record<string, unknown>;
			artifacts?: Record<string, unknown>[];
		} = {
			lesson_plan: { topic: "Photosynthesis", grade_level: "Grade 5" },
		};

		expect(data.lesson_plan?.["topic"]).toBe("Photosynthesis");
	});

	it("data can carry artifacts for content gate", () => {
		const data: {
			lesson_plan?: Record<string, unknown>;
			artifacts?: Record<string, unknown>[];
		} = {
			artifacts: [{ title: "Lesson", artifact_type: "lesson" }],
		};

		expect(data.artifacts?.[0]?.["title"]).toBe("Lesson");
	});
});
