"use client";

import { useCallback, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, gatewayUrl } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Types matching common/contracts/unit_view.py
// ---------------------------------------------------------------------------

export interface UnitSessionProgress {
	readonly session_id: string;
	readonly child_run_id: string | null;
	readonly status: "pending" | "generating" | "in_review" | "approved" | "failed" | "blocked";
	readonly progress_percent: number;
}

export interface UnitAggregate {
	readonly status: string;
	readonly total_sessions: number;
	readonly approved_sessions: number;
	readonly failed_sessions: number;
}

export interface UnitCoherenceWarning {
	readonly code: string;
	readonly message: string;
	readonly session_ids: readonly string[];
}

export interface SessionPlan {
	readonly session_id: string;
	readonly order_index: number;
	readonly title: string;
	readonly sub_topic: string;
	readonly duration_minutes: number;
	readonly learning_objectives: readonly string[];
	readonly bloom_level_primary: string;
	readonly methodology_primary: string;
	readonly prerequisite_sessions: readonly string[];
}

export interface UnitView {
	readonly parent: {
		readonly schema_version: string;
		readonly parent_run_id: string;
		readonly teacher_id: string;
		readonly topic: string;
	};
	readonly sequence: {
		readonly topic: string;
		readonly grade_level: string;
		readonly subject: string;
		readonly locale: string;
		readonly total_sessions: number;
		readonly sessions: readonly SessionPlan[];
		readonly grounding_status: string;
		readonly confidence: number;
		readonly rationale: string;
	};
	readonly sessions: readonly UnitSessionProgress[];
	readonly aggregate: UnitAggregate;
	readonly coherence_warnings: readonly UnitCoherenceWarning[];
	readonly cursor: number;
}

// ---------------------------------------------------------------------------
// Fetch helper (exported for testing)
// ---------------------------------------------------------------------------

export async function fetchUnitView(parentRunId: string): Promise<UnitView> {
	return apiClient.get<UnitView>(`/teaching-packs/units/${parentRunId}`);
}

// ---------------------------------------------------------------------------
// useUnit hook
// ---------------------------------------------------------------------------

export function useUnit(parentRunId: string) {
	const queryClient = useQueryClient();
	const sseRef = useRef<EventSource | null>(null);
	const cursorRef = useRef<number>(0);

	const query = useQuery({
		queryKey: ["unit", parentRunId],
		queryFn: () => fetchUnitView(parentRunId),
		enabled: Boolean(parentRunId),
		staleTime: 10_000,
	});

	// Track cursor from latest snapshot
	useEffect(() => {
		if (query.data) {
			cursorRef.current = query.data.cursor;
		}
	}, [query.data]);

	// SSE subscription with cursor reconciliation
	useEffect(() => {
		if (!parentRunId) return;

		const connect = () => {
			const url = `${gatewayUrl()}/teaching-packs/units/${parentRunId}/status?cursor=${cursorRef.current}`;
			const es = new EventSource(url, { withCredentials: true });
			sseRef.current = es;

			es.addEventListener("unit.session.status_changed", (ev) => {
				try {
					const payload = JSON.parse((ev as MessageEvent).data) as {
						cursor?: number;
						session_id?: string;
						status?: string;
					};
					// Stale delta — cursor already seen, discard
					if (typeof payload.cursor === "number" && payload.cursor <= cursorRef.current) {
						return;
					}
					if (typeof payload.cursor === "number") {
						cursorRef.current = payload.cursor;
					}
					queryClient.invalidateQueries({ queryKey: ["unit", parentRunId] });
				} catch {
					// malformed event — ignore
				}
			});

			es.addEventListener("unit.progress", (ev) => {
				try {
					const payload = JSON.parse((ev as MessageEvent).data) as { cursor?: number };
					if (typeof payload.cursor === "number" && payload.cursor > cursorRef.current) {
						cursorRef.current = payload.cursor;
						queryClient.invalidateQueries({ queryKey: ["unit", parentRunId] });
					}
				} catch {
					// ignore
				}
			});

			es.onerror = () => {
				es.close();
				// Reconnect: re-snapshot then re-subscribe
				setTimeout(() => {
					queryClient.invalidateQueries({ queryKey: ["unit", parentRunId] });
					connect();
				}, 2000);
			};
		};

		connect();

		return () => {
			sseRef.current?.close();
		};
	}, [parentRunId, queryClient]);

	// ---------------------------------------------------------------------------
	// Actions
	// ---------------------------------------------------------------------------

	const approveAll = useCallback(async (): Promise<Record<string, string>> => {
		const res = await apiClient.post<{ results: Record<string, string> }>(
			`/teaching-packs/units/${parentRunId}/approve-all`,
		);
		queryClient.invalidateQueries({ queryKey: ["unit", parentRunId] });
		return (res as { results: Record<string, string> }).results;
	}, [parentRunId, queryClient]);

	const spawnAnyway = useCallback(
		async (sessionId: string): Promise<void> => {
			await apiClient.post(
				`/teaching-packs/units/${parentRunId}/sessions/${sessionId}/spawn-anyway`,
			);
			queryClient.invalidateQueries({ queryKey: ["unit", parentRunId] });
		},
		[parentRunId, queryClient],
	);

	const exportUnit = useCallback(async (): Promise<{ status: string }> => {
		return apiClient.post<{ status: string }>(`/teaching-packs/units/${parentRunId}/export`);
	}, [parentRunId]);

	return {
		data: query.data,
		isLoading: query.isLoading,
		error: query.error,
		approveAll,
		spawnAnyway,
		exportUnit,
	};
}
