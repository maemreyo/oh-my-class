import type { SessionRole } from "@/lib/session-token";

/** One of the seven significant event types this stream ever emits (mirrors
 * `services/gateway/teaching_session/events.py::SessionEventType`). */
export type SessionEventName =
	| "session_started"
	| "slide_changed"
	| "interaction_opened"
	| "aggregate_updated"
	| "branch_selected"
	| "annotation_added"
	| "session_ended";

/** Base AC: minimal reading, clear next action. Never a data wall. */
export function nextActionHint(state: { readonly open_interaction_id: string | null; readonly ended: boolean }): string {
	if (state.ended) return "Session ended.";
	return state.open_interaction_id
		? "Review responses, then advance when ready."
		: "Present the current slide.";
}

/** Amendment #2: elapsed time on the *current* slide vs SDTF-02's
 * `planned_duration_minutes` -- only meaningful when a planned duration
 * exists; a slide with none is never "behind". */
export function isBehindPace(elapsedMs: number, plannedMinutes: number | null): boolean {
	if (!plannedMinutes || plannedMinutes <= 0) return false;
	return elapsedMs > plannedMinutes * 60_000;
}

/** Amendment #1: the ephemeral annotation overlay clears on slide change or
 * session end, and on nothing else. */
export function shouldClearAnnotation(eventName: SessionEventName | string): boolean {
	return eventName === "slide_changed" || eventName === "session_ended";
}

/** Base AC: teacher-only notes/AI suggestions and branch controls are
 * visible only to the controller role -- never display/student/observer. */
export function isControllerRole(role: SessionRole): boolean {
	return role === "controller";
}

/** One of the five branch content types (TSP-06 base AC1) -- mirrors
 * `services/gateway/teaching_session/branches.py::BranchContentType`. */
export type BranchContentType = "reteach" | "hint" | "simpler_example" | "challenge" | "extra_practice";

export const BRANCH_CONTENT_TYPES: readonly BranchContentType[] = [
	"reteach",
	"hint",
	"simpler_example",
	"challenge",
	"extra_practice",
];
