/**
 * SDE-08: pure logic tests for the shared "Rewrite with AI" trigger.
 *
 * DOM rendering isn't this repo's convention for slide-deck-editor
 * components (see deck-save.test.ts / version-history-panel.test.ts) -- this
 * tests the extracted pure precedence rule that decides whether a preset key
 * or freeform instruction is sent to the suggestion endpoint.
 */

import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api-client";
import { resolveRewriteSuggestionPayload, rewriteSuggestionErrorMessage } from "./block-rewrite-controls";

describe("resolveRewriteSuggestionPayload", () => {
	it("sends the preset key when freeform text is blank", () => {
		expect(resolveRewriteSuggestionPayload("shorter", "")).toEqual({ preset: "shorter" });
		expect(resolveRewriteSuggestionPayload("shorter", "   ")).toEqual({ preset: "shorter" });
	});

	it("sends trimmed freeform text (never a separate/looser shape) when it's non-blank, taking precedence over the selected preset", () => {
		expect(resolveRewriteSuggestionPayload("shorter", "  Make it rhyme.  ")).toEqual({ instruction: "Make it rhyme." });
	});
});

describe("rewriteSuggestionErrorMessage — SDE-10 teacher-safe error copy, never the raw ApiError", () => {
	it("maps a 429 (rate limit) to the pre-written rate-limit copy, not the raw detail/request-id message", () => {
		const err = new ApiError("ai_rewrite_rate_limited (request: abc-123)", 429);
		const message = rewriteSuggestionErrorMessage(err);
		expect(message).not.toContain("abc-123");
		expect(message).not.toContain("429");
		expect(message.length).toBeGreaterThan(0);
	});

	it("maps a 403 (feature disabled) to the pre-written disabled copy", () => {
		const err = new ApiError("slide_deck_ai_rewrite_disabled (request: abc-123)", 403);
		const message = rewriteSuggestionErrorMessage(err);
		expect(message).not.toContain("abc-123");
		expect(message.length).toBeGreaterThan(0);
	});

	it("falls back to a generic message for anything else, never crashing on a non-Error value", () => {
		expect(rewriteSuggestionErrorMessage(new ApiError("rewrite_unavailable (request: x)", 502)).length).toBeGreaterThan(0);
		expect(rewriteSuggestionErrorMessage("not an error object").length).toBeGreaterThan(0);
		expect(rewriteSuggestionErrorMessage(undefined).length).toBeGreaterThan(0);
	});
});
