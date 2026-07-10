/**
 * SDE-08: pure logic tests for the shared "Rewrite with AI" trigger.
 *
 * DOM rendering isn't this repo's convention for slide-deck-editor
 * components (see deck-save.test.ts / version-history-panel.test.ts) -- this
 * tests the extracted pure precedence rule that decides whether a preset key
 * or freeform instruction is sent to the suggestion endpoint.
 */

import { describe, expect, it } from "vitest";
import { resolveRewriteSuggestionPayload } from "./block-rewrite-controls";

describe("resolveRewriteSuggestionPayload", () => {
	it("sends the preset key when freeform text is blank", () => {
		expect(resolveRewriteSuggestionPayload("shorter", "")).toEqual({ preset: "shorter" });
		expect(resolveRewriteSuggestionPayload("shorter", "   ")).toEqual({ preset: "shorter" });
	});

	it("sends trimmed freeform text (never a separate/looser shape) when it's non-blank, taking precedence over the selected preset", () => {
		expect(resolveRewriteSuggestionPayload("shorter", "  Make it rhyme.  ")).toEqual({ instruction: "Make it rhyme." });
	});
});
