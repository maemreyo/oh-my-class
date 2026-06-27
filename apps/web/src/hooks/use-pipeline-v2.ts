"use client";

import { useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, gatewayUrl } from "@/lib/api-client";

export type PipelineV2RunStatus =
	| "pending"
	| "running"
	| "awaiting_approval"
	| "completed"
	| "failed"
	| "cancelled";

export type PipelineV2GateName =
	| "clarification_required"
	| "contract_confirmation"
	| "search_plan_confirmation"
	| "blueprint_approval"
	| "content_approval";

export type PipelineV2GateAction = "approve" | "edit" | "reject";

export interface PipelineV2CreateRunRequest {
	readonly raw_request: string;
	readonly class_info: Readonly<Record<string, unknown>>;
}

export interface PipelineV2RunAcceptedResponse {
	readonly run_id: string;
	readonly job_id: string | null;
	readonly status: PipelineV2RunStatus;
}

export interface PipelineV2ResumeRequest {
	readonly gate_id: string;
	readonly gate_name: PipelineV2GateName;
	readonly action: PipelineV2GateAction;
	readonly response?: Readonly<Record<string, unknown>>;
}

export interface PipelineV2ResumeAcceptedResponse {
	readonly run_id: string;
	readonly response_id: string;
	readonly job_id: string;
}

export interface ArtifactProgressItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: "queued" | "generating" | "rendering" | "validating" | "ready" | "failed";
	readonly error?: string;
}

export interface PipelineV2EventPayload {
	readonly sequence?: number;
	readonly gate_id?: string;
	readonly gate_name?: PipelineV2GateName;
	readonly gate?: PipelineV2GateName;
	readonly snapshot_ids?: readonly string[];
	readonly contract?: Readonly<Record<string, unknown>>;
	readonly questions?: readonly Readonly<Record<string, unknown>>[];
	readonly artifacts?: readonly ArtifactProgressItem[];
	readonly [key: string]: unknown;
}

export interface PipelineV2StatusEvent {
	readonly name: string;
	readonly payload: PipelineV2EventPayload;
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

export function useCreatePipelineV2Run() {
	const queryClient = useQueryClient();
	return useMutation<PipelineV2RunAcceptedResponse, Error, PipelineV2CreateRunRequest>({
		mutationFn: (request) =>
			apiClient.post<PipelineV2RunAcceptedResponse>("/pipeline-v2/run", request, {
				headers: { "Idempotency-Key": idempotencyKey("create") },
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["pipeline-v2", "runs"] });
		},
	});
}

export function useResumePipelineV2Run(runId: string) {
	const queryClient = useQueryClient();
	return useMutation<PipelineV2ResumeAcceptedResponse, Error, PipelineV2ResumeRequest>({
		mutationFn: (request) =>
			apiClient.post<PipelineV2ResumeAcceptedResponse>(
				`/pipeline-v2/run/${runId}/resume`,
				request,
				{ headers: { "Idempotency-Key": idempotencyKey(`resume:${runId}`) } },
			),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["pipeline-v2", "run", runId] });
		},
	});
}

	export function usePipelineV2Status(runId: string | null) {
		const lastEventIdRef = useRef<string | null>(null);
		const subscribe = useCallback((callback: (event: PipelineV2StatusEvent) => void) => {
			if (!runId) return () => {};
			let closed = false;
			let retryTimer: ReturnType<typeof setTimeout> | null = null;
			let eventSource: EventSource | null = null;

			const connect = () => {
				const url = new URL(`${gatewayUrl()}/pipeline-v2/run/${runId}/status`);
				if (lastEventIdRef.current) {
					url.searchParams.set("last_event_id", lastEventIdRef.current);
				}
				eventSource = new EventSource(url.toString());
				for (const eventName of PIPELINE_V2_EVENT_NAMES) {
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
	return `${gatewayUrl()}/pipeline-v2/run/${runId}/snapshots/${snapshotId}/preview?view=${view}`;
}

function parsePayload(data: string): PipelineV2EventPayload {
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

const PIPELINE_V2_EVENT_NAMES = [
	"pipeline_v2.run.accepted",
	"pipeline_v2.clarification_required.opened",
	"pipeline_v2.contract_confirmation.opened",
	"pipeline_v2.search_plan_confirmation.opened",
	"pipeline_v2.blueprint_approval.opened",
	"pipeline_v2.content_approval.opened",
	"pipeline_v2.content.approved_snapshots",
	"pipeline_v2.run.cancelled",
] as const;
