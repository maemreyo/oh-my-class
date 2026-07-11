"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { gatewayUrl } from "@/lib/api-client";
import { applyLiveEvent, connectionStateOnError } from "./teaching-session-live-reducer";

export type SessionConnectionState = "connecting" | "connected" | "reconnecting" | "offline";

export interface TeachingSessionTally {
	readonly attempt_count: number;
	readonly correct_count: number;
}

export interface TeachingSessionReadModel {
	readonly current_slide_id: string | null;
	readonly current_branch_id: string | null;
	readonly open_interaction_id: string | null;
	readonly tallies: Readonly<Record<string, TeachingSessionTally>>;
	readonly ended: boolean;
	/** Fetch `GET /teaching-sessions/{sessionId}/content` for the actual
	 * slide content when this changes -- this field is just the pointer
	 * (mirrors `services/gateway/routers/teaching_session_live.py`'s
	 * `SessionContentResponse`), never the content itself. */
	readonly current_snapshot_id: string | null;
}

export interface TeachingSessionLiveEvent {
	readonly name: string;
	readonly payload: Readonly<Record<string, unknown>>;
}

const INITIAL_STATE: TeachingSessionReadModel = {
	current_slide_id: null,
	current_branch_id: null,
	open_interaction_id: null,
	tallies: {},
	ended: false,
	current_snapshot_id: null,
};

/**
 * Live session state + connection status for the teaching cockpit (TSP-04).
 *
 * Connects to `GET /teaching-sessions/{sessionId}/stream` (services/gateway/
 * routers/teaching_session_live.py). Unlike `useTeachingPackStatus` (apps/web/
 * src/hooks/use-teaching-packs.ts), this relies on the browser's *native* SSE
 * reconnect (which auto-resends `Last-Event-ID`) rather than hand-rolling
 * reconnect-with-query-param -- the gateway route replays missed events from
 * that header itself, so there's nothing left for this hook to do on
 * reconnect except reflect the state.
 *
 * State is folded from event payloads directly, mirroring in miniature
 * `teaching_session/events.py`'s `apply_event` last-write-wins reducer --
 * ponytail: duplicates that reducer's shape instead of importing it (it's a
 * Python module); upgrade to a shared generated type/reducer if the two
 * drift.
 */
export function useTeachingSessionLive(sessionId: string | null, sessionToken: string | null) {
	const [connection, setConnection] = useState<SessionConnectionState>("connecting");
	const [state, setState] = useState<TeachingSessionReadModel>(INITIAL_STATE);
	const listenersRef = useRef<Set<(event: TeachingSessionLiveEvent) => void>>(new Set());

	const onEvent = useCallback((callback: (event: TeachingSessionLiveEvent) => void) => {
		listenersRef.current.add(callback);
		return () => listenersRef.current.delete(callback);
	}, []);

	useEffect(() => {
		if (!sessionId || !sessionToken) {
			setConnection("offline");
			return;
		}
		let cancelled = false;
		setConnection("connecting");
		setState(INITIAL_STATE);

		const seed = async () => {
			try {
				const response = await fetch(`${gatewayUrl()}/teaching-sessions/${sessionId}/state`, {
					headers: { Authorization: `Bearer ${sessionToken}` },
				});
				if (!response.ok || cancelled) return;
				const data = (await response.json()) as {
					current_slide_id: string | null;
					current_branch_id: string | null;
					open_interaction_id: string | null;
					tallies: Record<string, TeachingSessionTally>;
					ended: boolean;
					current_snapshot_id: string | null;
				};
				if (cancelled) return;
				setState({
					current_slide_id: data.current_slide_id,
					current_branch_id: data.current_branch_id,
					open_interaction_id: data.open_interaction_id,
					tallies: data.tallies ?? {},
					ended: data.ended,
					current_snapshot_id: data.current_snapshot_id ?? null,
				});
			} catch {
				// ponytail: best-effort seed -- the stream's own replay-from-
				// Last-Event-ID still carries full history if this fetch fails.
			}
		};
		void seed();

		const url = new URL(`${gatewayUrl()}/teaching-sessions/${sessionId}/stream`);
		// EventSource can't set an Authorization header -- see
		// `get_session_claims_for_stream`'s docstring for the matching
		// query-param fallback on the gateway side.
		url.searchParams.set("session_token", sessionToken);
		const eventSource = new EventSource(url.toString());

		eventSource.onopen = () => {
			if (!cancelled) setConnection("connected");
		};
		eventSource.onerror = () => {
			// Native EventSource auto-retries (readyState stays CONNECTING)
			// unless the browser gave up (readyState CLOSED) -- reflect both
			// without tearing down the connection ourselves.
			if (cancelled) return;
			setConnection(connectionStateOnError(eventSource.readyState));
		};

		const applyEvent = (eventType: string) => (event: MessageEvent) => {
			let payload: Record<string, unknown> = {};
			try {
				payload = JSON.parse(event.data as string) as Record<string, unknown>;
			} catch {
				return;
			}
			for (const listener of listenersRef.current) listener({ name: eventType, payload });
			setState((prev) => applyLiveEvent(prev, eventType, payload));
		};

		for (const eventType of SESSION_EVENT_TYPES) {
			eventSource.addEventListener(eventType, applyEvent(eventType) as EventListener);
		}

		return () => {
			cancelled = true;
			eventSource.close();
		};
	}, [sessionId, sessionToken]);

	return { connection, state, onEvent };
}

const SESSION_EVENT_TYPES = [
	"session_started",
	"slide_changed",
	"interaction_opened",
	"aggregate_updated",
	"branch_selected",
	"annotation_added",
	"session_ended",
	"content_republished",
] as const;
