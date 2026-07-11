import { describe, expect, it } from "vitest";
import { applyLiveEvent, connectionStateOnError } from "./teaching-session-live-reducer";
import type { TeachingSessionReadModel } from "./use-teaching-session-live";

const INITIAL: TeachingSessionReadModel = {
	current_slide_id: null,
	current_branch_id: null,
	open_interaction_id: null,
	tallies: {},
	ended: false,
	current_snapshot_id: null,
};

describe("connectionStateOnError", () => {
	it("stays reconnecting while the browser is still retrying (readyState CONNECTING)", () => {
		expect(connectionStateOnError(0)).toBe("reconnecting");
	});

	it("goes offline once the browser gives up (readyState CLOSED)", () => {
		expect(connectionStateOnError(2)).toBe("offline");
	});
});

describe("applyLiveEvent", () => {
	it("folds slide_changed into current_slide_id", () => {
		const next = applyLiveEvent(INITIAL, "slide_changed", { slide_id: "slide-2" });
		expect(next.current_slide_id).toBe("slide-2");
	});

	it("folds branch_selected into both slide and branch id", () => {
		const next = applyLiveEvent(INITIAL, "branch_selected", { slide_id: "slide-3", branch_id: "branch-a" });
		expect(next.current_slide_id).toBe("slide-3");
		expect(next.current_branch_id).toBe("branch-a");
	});

	it("folds interaction_opened into open_interaction_id", () => {
		const next = applyLiveEvent(INITIAL, "interaction_opened", { interaction_id: "int-1" });
		expect(next.open_interaction_id).toBe("int-1");
	});

	it("merges aggregate_updated tallies without dropping other interactions", () => {
		const withFirst = applyLiveEvent(INITIAL, "aggregate_updated", {
			interaction_id: "int-1",
			tallies: { attempt_count: 5, correct_count: 3 },
		});
		const withSecond = applyLiveEvent(withFirst, "aggregate_updated", {
			interaction_id: "int-2",
			tallies: { attempt_count: 2, correct_count: 2 },
		});
		expect(withSecond.tallies).toEqual({
			"int-1": { attempt_count: 5, correct_count: 3 },
			"int-2": { attempt_count: 2, correct_count: 2 },
		});
	});

	it("marks ended on session_ended", () => {
		const next = applyLiveEvent(INITIAL, "session_ended", {});
		expect(next.ended).toBe(true);
	});

	it("folds content_republished into current_snapshot_id", () => {
		const next = applyLiveEvent(INITIAL, "content_republished", { snapshot_id: "snap-2" });
		expect(next.current_snapshot_id).toBe("snap-2");
	});

	it("is a no-op for events with no derived read-model field (mirrors apply_event)", () => {
		const next = applyLiveEvent(INITIAL, "session_started", { deck_id: "d1", snapshot_id: "s1" });
		expect(next).toEqual(INITIAL);
	});

	it("is a no-op for an unknown event type", () => {
		const next = applyLiveEvent(INITIAL, "not_a_real_event", {});
		expect(next).toEqual(INITIAL);
	});
});
