"use client";

import { useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, gatewayUrl } from "@/lib/api-client";
import type {
	TeachingPackCreateRunRequest,
	TeachingPackGateName,
	TeachingPackResumeAcceptedResponse,
	TeachingPackResumeRequest,
	TeachingPackRunAcceptedResponse,
	TeachingPackRunStatusResponse,
} from "@/types/teaching-pack-api";

export type {
	TeachingPackCreateRunRequest,
	TeachingPackGateAction,
	TeachingPackGateName,
	TeachingPackResumeAcceptedResponse,
	TeachingPackResumeRequest,
	TeachingPackRunAcceptedResponse,
	TeachingPackRunStatus,
	TeachingPackRunStatusResponse,
} from "@/types/teaching-pack-api";

export interface ArtifactProgressItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: "queued" | "generating" | "rendering" | "validating" | "ready" | "failed";
	readonly error?: string;
}

export interface TeachingPackEventPayload {
	readonly sequence?: number;
	readonly gate_id?: string;
	readonly gate_name?: TeachingPackGateName;
	readonly gate?: TeachingPackGateName;
	readonly snapshot_ids?: readonly string[];
	readonly contract?: Readonly<Record<string, unknown>>;
	readonly questions?: readonly Readonly<Record<string, unknown>>[];
	readonly artifacts?: readonly ArtifactProgressItem[];
	readonly [key: string]: unknown;
}

export interface TeachingPackStatusEvent {
	readonly name: string;
	readonly payload: TeachingPackEventPayload;
}

export interface RenderedSnapshotMetadata {
	readonly snapshot_id: string;
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly content_hash: string;
	readonly html_hash: string;
	readonly renderer_version: string;
	readonly template_version: string;
	readonly theme_version: string;
	readonly standalone_valid: boolean;
	readonly approved_at: string | null;
}

export function useCreateTeachingPackRun() {
	const queryClient = useQueryClient();
	return useMutation<TeachingPackRunAcceptedResponse, Error, TeachingPackCreateRunRequest>({
		mutationFn: (request) =>
			apiClient.post<TeachingPackRunAcceptedResponse>("/teaching-packs/runs", request, {
				headers: { "Idempotency-Key": idempotencyKey("create") },
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["teaching-pack", "runs"] });
		},
	});
}

export function useResumeTeachingPackRun(runId: string) {
	const queryClient = useQueryClient();
	return useMutation<TeachingPackResumeAcceptedResponse, Error, TeachingPackResumeRequest>({
		mutationFn: (request) =>
			apiClient.post<TeachingPackResumeAcceptedResponse>(
				`/teaching-packs/runs/${runId}/resume`,
				request,
				{ headers: { "Idempotency-Key": idempotencyKey(`resume:${runId}`) } },
			),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["teaching-pack", "run", runId] });
		},
	});
}

export function useTeachingPackRun(runId: string | null) {
	return {
		queryKey: ["teaching-pack", "run", runId] as const,
		queryFn: async () => {
			if (!runId) throw new Error("No run ID");
			return apiClient.get<TeachingPackRunStatusResponse>(`/teaching-packs/runs/${runId}`);
		},
		enabled: !!runId,
	};
}

export function useTeachingPackStatus(runId: string | null) {
	const lastEventIdRef = useRef<string | null>(null);
	const subscribe = useCallback((callback: (event: TeachingPackStatusEvent) => void) => {
		if (!runId) return () => {};
		let closed = false;
		let retryTimer: ReturnType<typeof setTimeout> | null = null;
		let eventSource: EventSource | null = null;

		const connect = () => {
			const url = new URL(`${gatewayUrl()}/teaching-packs/runs/${runId}/status`);
			if (lastEventIdRef.current) {
				url.searchParams.set("last_event_id", lastEventIdRef.current);
			}
			eventSource = new EventSource(url.toString(), { withCredentials: true });
			for (const eventName of TEACHING_PACK_EVENT_NAMES) {
				eventSource.addEventListener(eventName, handleMessage);
			}
			eventSource.onerror = () => {
				eventSource?.close();
				if (!closed) retryTimer = setTimeout(connect, 1_000);
			};
		};

		const handleMessage = (event: Event) => {
			if (event instanceof MessageEvent && typeof event.data === "string") {
				if (event.lastEventId) lastEventIdRef.current = event.lastEventId;
				callback({ name: event.type, payload: parsePayload(event.data) });
			}
		};
		connect();
		return () => {
			closed = true;
			if (retryTimer) clearTimeout(retryTimer);
			eventSource?.close();
		};
	}, [runId]);
	return { subscribe };
}

export function snapshotPreviewUrl(
	runId: string,
	snapshotId: string,
	view: "student" | "teacher",
): string {
	return `${gatewayUrl()}/teaching-packs/runs/${runId}/snapshots/${snapshotId}/preview?view=${view}`;
}

function parsePayload(data: string): TeachingPackEventPayload {
	try {
		const parsed: unknown = JSON.parse(data);
		if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
			return Object.fromEntries(Object.entries(parsed));
		}
		return {};
	} catch (error) {
		if (error instanceof SyntaxError) return {};
		throw error;
	}
}

function idempotencyKey(prefix: string): string {
	if (typeof window !== "undefined" && window.crypto?.randomUUID) {
		return `${prefix}:${window.crypto.randomUUID()}`;
	}
	return `${prefix}:${Date.now().toString(36)}`;
}

const TEACHING_PACK_EVENT_NAMES = [
	"teaching_pack.run.accepted",
	"teaching_pack.clarification_required.opened",
	"teaching_pack.contract_confirmation.opened",
	"teaching_pack.search_plan_confirmation.opened",
	"teaching_pack.blueprint_approval.opened",
	"teaching_pack.content_approval.opened",
	"teaching_pack.content.approved_snapshots",
	"teaching_pack.run.cancelled",
] as const;
