"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface PacingNudgePreference {
	readonly enabled: boolean;
}

const QUERY_KEY = ["teaching-session", "pacing-nudge-preference"] as const;

/**
 * TSP-04 amendment #2: the cockpit's pacing nudge is opt-in per teacher, not
 * default-on. Backed by `GET/PUT /teaching-sessions/preferences/pacing-nudge`
 * (services/gateway/routers/teaching_session_live.py), which in turn reads/
 * writes `packages/agents/teaching_pack/teacher_memory.py`'s
 * `read_pacing_nudge_preference`/`write_pacing_nudge_preference` -- the same
 * per-teacher memory store TSP-05's gamification opt-in already uses. This
 * route is gated by the normal account JWT (`apiClient` attaches it via
 * cookie automatically), not a session-role token -- it's a per-teacher
 * setting, not scoped to one live session.
 */
export function usePacingNudgePreference() {
	return useQuery<PacingNudgePreference>({
		queryKey: QUERY_KEY,
		queryFn: () => apiClient.get<PacingNudgePreference>("/teaching-sessions/preferences/pacing-nudge"),
	});
}

export function useSetPacingNudgePreference() {
	const queryClient = useQueryClient();
	return useMutation<PacingNudgePreference, Error, boolean>({
		mutationFn: (enabled) =>
			apiClient.put<PacingNudgePreference>("/teaching-sessions/preferences/pacing-nudge", { enabled }),
		onSuccess: (data) => {
			queryClient.setQueryData(QUERY_KEY, data);
		},
	});
}
