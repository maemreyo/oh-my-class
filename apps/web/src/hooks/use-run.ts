"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Run } from "@/types";

export function useRuns() {
	return useQuery({
		queryKey: ["runs"],
		queryFn: () => apiClient.get<Run[]>("/run"),
	});
}

export function useRun(runId: string) {
	return useQuery({
		queryKey: ["runs", runId],
		queryFn: () => apiClient.get<Run>(`/run/${runId}`),
		enabled: !!runId,
	});
}

export function useCreateRun() {
	const queryClient = useQueryClient();
	return useMutation({
		mutationFn: (data: {
			raw_request: string;
			class_info: Record<string, unknown>;
		}) => apiClient.post<Run>("/run", data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["runs"] });
		},
	});
}
