"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { RunResponse } from "@/hooks/use-run";

export interface ApprovalRequest {
	action: "approve" | "edit" | "reject";
	feedback?: string;
	edits?: Record<string, unknown>;
}

export interface ApprovalResponse {
	status: string;
	message: string;
	run_id: string;
}

export function useApproveRun(runId: string) {
	return useMutation<ApprovalResponse, Error, ApprovalRequest>({
		mutationFn: async (request) => {
			const endpoint =
				request.action === "reject"
					? `/run/${runId}/reject`
					: `/run/${runId}/approve`;
			return apiClient.post<ApprovalResponse>(endpoint, request);
		},
	});
}

export function useRejectRun(runId: string) {
	return useMutation<ApprovalResponse, Error, { feedback: string }>({
		mutationFn: async ({ feedback }) => {
			return apiClient.post<ApprovalResponse>(`/run/${runId}/reject`, {
				action: "reject",
				feedback,
			});
		},
	});
}

// ── Legacy hooks used by approvals/page.tsx ───────────────────────────────────

export function usePendingApprovals() {
	return { data: [] as RunResponse[], isLoading: false };
}

export function useApprove() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (runId: string) =>
			apiClient.post(`/run/${runId}/approve`, { action: "approve" }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["runs"] });
			queryClient.invalidateQueries({ queryKey: ["approvals"] });
		},
	});
}

export function useReject() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: ({ runId, feedback }: { runId: string; feedback: string }) =>
			apiClient.post(`/run/${runId}/reject`, {
				action: "reject",
				feedback,
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["runs"] });
			queryClient.invalidateQueries({ queryKey: ["approvals"] });
		},
	});
}
