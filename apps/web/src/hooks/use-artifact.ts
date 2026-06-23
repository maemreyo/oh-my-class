"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Artifact } from "@/types";

export function useArtifacts(runId: string) {
	return useQuery({
		queryKey: ["artifacts", runId],
		queryFn: () => apiClient.get<Artifact[]>(`/run/${runId}/artifacts`),
		enabled: !!runId,
	});
}

export function useArtifact(runId: string, artifactId: string) {
	return useQuery({
		queryKey: ["artifacts", runId, artifactId],
		queryFn: () =>
			apiClient.get<Artifact>(`/run/${runId}/artifacts/${artifactId}`),
		enabled: !!runId && !!artifactId,
	});
}
