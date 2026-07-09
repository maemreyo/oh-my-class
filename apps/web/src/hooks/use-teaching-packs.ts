"use client";

import { useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, gatewayUrl } from "@/lib/api-client";
import type {
	ArtifactStatusItem,
	ArtifactExplanation,
	TeachingPackCreateRunRequest,
	TeachingPackGateName,
	TeachingPackResumeAcceptedResponse,
	TeachingPackResumeRequest,
	TeachingPackRevisionAcceptedResponse,
	TeachingPackRunAcceptedResponse,
	TeachingPackRunStatusResponse,
} from "@/types/teaching-pack-api";

export type {
	ArtifactExplanation,
	TeachingPackCreateRunRequest,
	TeachingPackGateAction,
	TeachingPackGateName,
	TeachingPackResumeAcceptedResponse,
	TeachingPackResumeRequest,
	TeachingPackRevisionAcceptedResponse,
	TeachingPackRunAcceptedResponse,
	TeachingPackRunStatus,
	TeachingPackRunStatusResponse,
} from "@/types/teaching-pack-api";

export interface ArtifactProgressItem {
	readonly artifact_id: string;
	readonly artifact_type: string;
	readonly status: "queued" | "generating" | "rendering" | "validating" | "ready" | "failed" | "passed" | "regenerating" | "skipped_due_dependency" | "escalated";
	readonly summary?: string;
	readonly teacher_action?: string;
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
	readonly artifact_statuses?: readonly ArtifactStatusItem[];
	readonly artifact_explanations?: readonly ArtifactExplanation[];
	readonly auto_approved?: boolean;
	readonly escalated?: boolean;
	readonly needs_review?: boolean;
	readonly approval_mode?: string;
	readonly escalate_reason?: string;
	readonly trust_score?: number;
	readonly revert_window_seconds?: number;
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

export function useRequestArtifactRevision(runId: string) {
	const queryClient = useQueryClient();
	return useMutation<TeachingPackRevisionAcceptedResponse, Error, { readonly artifact_id: string; readonly feedback: string }>({
		mutationFn: (request) =>
			apiClient.post<TeachingPackRevisionAcceptedResponse>(
				`/teaching-packs/runs/${runId}/artifacts/${request.artifact_id}/request-revision`,
				{ feedback: request.feedback },
				{ headers: { "Idempotency-Key": idempotencyKey(`revision:${runId}:${request.artifact_id}`) } },
			),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["teaching-pack", "run", runId] });
		},
	});
}

export interface TranslateSlideDeckResponse {
	readonly run_id: string;
	readonly source_snapshot_id: string;
	readonly snapshot_id: string;
	readonly deck_id: string;
}

export function useTranslateSlideDeck(runId: string) {
	const queryClient = useQueryClient();
	return useMutation<TranslateSlideDeckResponse, Error, { readonly snapshot_id: string; readonly target_language: "en" | "vi" }>({
		mutationFn: (request) =>
			apiClient.post<TranslateSlideDeckResponse>(
				`/teaching-packs/runs/${runId}/snapshots/${request.snapshot_id}/translate`,
				{ target_language: request.target_language },
				{ headers: { "Idempotency-Key": idempotencyKey(`translate:${runId}:${request.snapshot_id}`) } },
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
	view: "student" | "teacher" | "print",
): string {
	return `${gatewayUrl()}/teaching-packs/runs/${runId}/snapshots/${snapshotId}/preview?view=${view}`;
}

// ADR-043 (SDH-01/SDH-04): slide-deck-specific display preferences, hand-
// mirrored here the same way SDH-01 mirrored the Python contract into
// `packages/renderer/src/contracts/slide_deck.ts` -- apps/web has no wired
// import path into that package's build output, so the shape is duplicated
// at this boundary instead of imported across the workspace.
export type SlideDeckDisplaySurface = "presentation" | "student" | "teacher" | "print" | "review";
export type SlideDeckPrintLayout = "paged" | "continuous";
export type SlideDeckSlidesPerPage = 1 | 2 | 4 | 6;
export type SlideDeckChromeVisibility = "hidden" | "minimal" | "branded";

export type SlideDeckDisplayPreferences = Readonly<{
	surface: SlideDeckDisplaySurface;
	print_layout: SlideDeckPrintLayout;
	slides_per_page: SlideDeckSlidesPerPage;
	chrome: SlideDeckChromeVisibility;
}>;

export const SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS: SlideDeckDisplayPreferences = {
	surface: "presentation",
	print_layout: "paged",
	slides_per_page: 1,
	chrome: "hidden",
};

/**
 * Build the slide-deck preview/export request from the typed preferences
 * shape (surface/print_layout/slides_per_page/chrome) instead of an
 * ad-hoc query string -- the gateway's `/preview` route resolves this
 * exact shape through `resolve_slide_deck_display_preferences` (see
 * `services/gateway/routers/teaching_pack_previews.py`).
 */
export function slideDeckPreviewUrl(
	runId: string,
	snapshotId: string,
	preferences: SlideDeckDisplayPreferences,
): string {
	const params = new URLSearchParams({
		surface: preferences.surface,
		print_layout: preferences.print_layout,
		slides_per_page: String(preferences.slides_per_page),
		chrome: preferences.chrome,
	});
	return `${gatewayUrl()}/teaching-packs/runs/${runId}/snapshots/${snapshotId}/preview?${params.toString()}`;
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
	"teaching_pack.artifact_workflow.status_changed",
	"teaching_pack.content_version.created",
	"teaching_pack.content.approved_snapshots",
	"teaching_pack.run.cancelled",
	"stage_transition",
	"gate_decision",
	"healing_decision",
	"escalate",
	"breaker_tripped",
] as const;
