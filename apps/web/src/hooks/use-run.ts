"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface RunRequest {
	raw_request: string;
	class_info: {
		grade: number;
		subject: string;
		student_count?: number;
		language?: string;
	};
	teacher_id: string;
}

export interface RunResponse {
	run_id: string;
	status: string;
	state?: Record<string, unknown>;
	// Legacy fields used by existing dashboard components
	topic?: string;
	current_step?: number;
}

export function useRuns() {
	return useQuery({
		queryKey: ["runs"],
		queryFn: () => apiClient.get<RunResponse[]>("/run"),
	});
}

export function useRun(runId: string | null) {
	return useQuery<RunResponse>({
		queryKey: ["run", runId],
		queryFn: async () => {
			if (!runId) throw new Error("No run ID");
			return apiClient.get<RunResponse>(`/run/${runId}`);
		},
		enabled: !!runId,
		refetchInterval: 5000,
	});
}

export function useCreateRun() {
	const queryClient = useQueryClient();
	return useMutation<RunResponse, Error, RunRequest>({
		mutationFn: async (request) => {
			return apiClient.post<RunResponse>("/run", request);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["runs"] });
		},
	});
}

export function useRunStatus(runId: string | null) {
	const subscribe = (callback: (event: MessageEvent) => void) => {
		if (!runId) return () => {};

		const eventSource = new EventSource(
			`${process.env.NEXT_PUBLIC_GATEWAY_URL}/run/${runId}/status`,
		);

		eventSource.addEventListener("interrupt", callback as EventListener);
		eventSource.addEventListener("gate_approved", callback as EventListener);
		eventSource.addEventListener("gate_rejected", callback as EventListener);
		eventSource.addEventListener("run_created", callback as EventListener);
		eventSource.addEventListener("step_completed", callback as EventListener);
		eventSource.addEventListener("run_failed", callback as EventListener);
		eventSource.onerror = (error) => {
			console.error("SSE error:", error);
		};

		return () => eventSource.close();
	};

	return { subscribe };
}
