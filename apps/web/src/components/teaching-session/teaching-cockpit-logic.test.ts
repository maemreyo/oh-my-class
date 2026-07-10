import { describe, expect, it } from "vitest";
import { isBehindPace, isControllerRole, nextActionHint, shouldClearAnnotation } from "./teaching-cockpit-logic";

describe("nextActionHint", () => {
	it("prompts to present when no interaction is open", () => {
		expect(nextActionHint({ open_interaction_id: null, ended: false })).toBe("Present the current slide.");
	});

	it("prompts to review responses when an interaction is open", () => {
		expect(nextActionHint({ open_interaction_id: "int-1", ended: false })).toBe(
			"Review responses, then advance when ready.",
		);
	});

	it("reports session end regardless of open interaction", () => {
		expect(nextActionHint({ open_interaction_id: "int-1", ended: true })).toBe("Session ended.");
	});
});

describe("isBehindPace", () => {
	it("is never behind when no planned duration exists", () => {
		expect(isBehindPace(10 * 60_000, null)).toBe(false);
	});

	it("is behind once elapsed time exceeds the planned minutes", () => {
		expect(isBehindPace(6 * 60_000, 5)).toBe(true);
	});

	it("is not behind while still within the planned minutes", () => {
		expect(isBehindPace(4 * 60_000, 5)).toBe(false);
	});
});

describe("shouldClearAnnotation", () => {
	it("clears on slide change", () => {
		expect(shouldClearAnnotation("slide_changed")).toBe(true);
	});

	it("clears on session end", () => {
		expect(shouldClearAnnotation("session_ended")).toBe(true);
	});

	it("does not clear on unrelated events", () => {
		expect(shouldClearAnnotation("aggregate_updated")).toBe(false);
		expect(shouldClearAnnotation("branch_selected")).toBe(false);
	});
});

describe("isControllerRole", () => {
	it("is true only for the controller role", () => {
		expect(isControllerRole("controller")).toBe(true);
		expect(isControllerRole("display")).toBe(false);
		expect(isControllerRole("student")).toBe(false);
		expect(isControllerRole("observer")).toBe(false);
	});
});
