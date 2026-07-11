import type { TeachingSessionReadModel, TeachingSessionTally } from "./use-teaching-session-live";

/** `EventSource.readyState` on error: still retrying (0=CONNECTING) vs the
 * browser gave up (2=CLOSED). Pulled out of the hook so the degraded/
 * reconnecting/offline transition is unit-testable without a real
 * `EventSource` or a React render loop. */
export function connectionStateOnError(readyState: number): "offline" | "reconnecting" {
	return readyState === 2 /* EventSource.CLOSED */ ? "offline" : "reconnecting";
}

/**
 * Fold one live-stream event into the read model. Mirrors, in miniature,
 * `services/gateway/teaching_session/events.py::apply_event`'s last-write-
 * wins reducer -- see that module for the authoritative version this must
 * stay compatible with.
 */
export function applyLiveEvent(
	prev: TeachingSessionReadModel,
	eventName: string,
	payload: Readonly<Record<string, unknown>>,
): TeachingSessionReadModel {
	switch (eventName) {
		case "slide_changed":
			return { ...prev, current_slide_id: (payload.slide_id as string) ?? prev.current_slide_id };
		case "branch_selected":
			return {
				...prev,
				current_slide_id: (payload.slide_id as string) ?? prev.current_slide_id,
				current_branch_id: (payload.branch_id as string) ?? prev.current_branch_id,
			};
		case "interaction_opened":
			return { ...prev, open_interaction_id: (payload.interaction_id as string) ?? prev.open_interaction_id };
		case "aggregate_updated": {
			const interactionId = payload.interaction_id as string | undefined;
			if (!interactionId) return prev;
			return {
				...prev,
				tallies: { ...prev.tallies, [interactionId]: payload.tallies as TeachingSessionTally },
			};
		}
		case "session_ended":
			return { ...prev, ended: true };
		case "content_republished":
			return {
				...prev,
				current_snapshot_id: (payload.snapshot_id as string) ?? prev.current_snapshot_id,
			};
		default:
			return prev;
	}
}
