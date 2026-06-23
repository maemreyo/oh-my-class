"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Run } from "@/types";

export function usePendingApprovals() {
	return useQuery({
		queryKey: ["approvals", "pending"],
		queryFn: () => apiClient.get<Run[]>("/run?status=awaiting_approval"),
	});
}

export function useApprove() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (runId: string) => apiClient.post(`/run/${runId}/approve`, {}),
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
			apiClient.post(`/run/${runId}/reject`, { feedback }),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["runs"] });
			queryClient.invalidateQueries({ queryKey: ["approvals"] });
		},
	});
}
