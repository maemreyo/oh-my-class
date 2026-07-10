"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type {
	TeachingBrief,
	TeachingBriefContractPreviewResponse,
	TeachingBriefLaunchResponse,
	TeachingBriefResponse,
} from "@/types/teaching-pack-api";

export function useTeachingBrief(briefId: string | null) {
	return useQuery<TeachingBriefResponse>({
		queryKey: ["teaching-brief", briefId],
		queryFn: () => apiClient.get<TeachingBriefResponse>(`/teaching-packs/briefs/${briefId}`),
		enabled: briefId !== null,
	});
}

export function useTeachingBriefContractPreview(briefId: string | null) {
	return useQuery<TeachingBriefContractPreviewResponse>({
		queryKey: ["teaching-brief-contract-preview", briefId],
		queryFn: () =>
			apiClient.get<TeachingBriefContractPreviewResponse>(
				`/teaching-packs/briefs/${briefId}/contract-preview`,
			),
		enabled: briefId !== null,
	});
}

export function useCreateTeachingBrief() {
	const queryClient = useQueryClient();
	return useMutation<TeachingBriefResponse, Error, TeachingBrief>({
		mutationFn: (brief) => apiClient.post<TeachingBriefResponse>("/teaching-packs/briefs", brief),
		onSuccess: (brief) => {
			queryClient.setQueryData(["teaching-brief", brief.brief_id], brief);
			void queryClient.invalidateQueries({ queryKey: ["teaching-brief-contract-preview", brief.brief_id] });
		},
	});
}

export function useAutosaveTeachingBrief(briefId: string | null) {
	const queryClient = useQueryClient();
	return useMutation<TeachingBriefResponse, Error, TeachingBrief>({
		mutationFn: (brief) => {
			if (!briefId) throw new Error("No teaching brief to autosave");
			return apiClient.put<TeachingBriefResponse>(`/teaching-packs/briefs/${briefId}`, brief);
		},
		onSuccess: (brief) => {
			queryClient.setQueryData(["teaching-brief", brief.brief_id], brief);
			void queryClient.invalidateQueries({ queryKey: ["teaching-brief-contract-preview", brief.brief_id] });
		},
	});
}

export function useLaunchTeachingBrief(briefId: string | null) {
	return useMutation<TeachingBriefLaunchResponse, Error, void>({
		mutationFn: () => {
			if (!briefId) throw new Error("Save the teaching brief before launch");
			return apiClient.post<TeachingBriefLaunchResponse>(`/teaching-packs/briefs/${briefId}/launch`);
		},
	});
}
