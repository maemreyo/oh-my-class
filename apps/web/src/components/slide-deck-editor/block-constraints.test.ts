import {
	SlideDeckBlockSchema,
	SlideDeckInteractionOptionSchema,
	SlideDeckInteractionSchema,
	SlideDeckInteractionTeacherOnlySchema,
	SlideDeckMediaSchema,
} from "@oh-my-class/schemas";
import { describe, expect, it } from "vitest";
import {
	BLOCK_BODY_MAX,
	BLOCK_BODY_MIN,
	INTERACTION_PROMPT_MAX,
	INTERACTION_PROMPT_MIN,
	MEDIA_ALT_TEXT_MAX,
	MEDIA_ALT_TEXT_MIN,
	OPTION_LABEL_MAX,
	OPTION_LABEL_MIN,
	RATIONALE_MAX,
	RATIONALE_MIN,
	clampOrReject,
} from "./block-constraints";

describe("hardcoded bounds match the generated registry schema (drift guard)", () => {
	// These constants are hardcoded (see block-constraints.ts for why — Turbopack
	// can't bundle a value-import of @oh-my-class/schemas' TS source in the
	// browser). This test is what keeps them honest: it runs under vitest,
	// which resolves the real schema fine, and fails the moment the Python
	// contract's Field(...) constraints change without this file being updated.
	it("block body", () => {
		expect(BLOCK_BODY_MIN).toBe(SlideDeckBlockSchema.shape.body.minLength);
		expect(BLOCK_BODY_MAX).toBe(SlideDeckBlockSchema.shape.body.maxLength);
	});

	it("media alt text", () => {
		expect(MEDIA_ALT_TEXT_MIN).toBe(SlideDeckMediaSchema.shape.alt_text.minLength);
		expect(MEDIA_ALT_TEXT_MAX).toBe(SlideDeckMediaSchema.shape.alt_text.maxLength);
	});

	it("interaction prompt", () => {
		expect(INTERACTION_PROMPT_MIN).toBe(SlideDeckInteractionSchema.shape.prompt.minLength);
		expect(INTERACTION_PROMPT_MAX).toBe(SlideDeckInteractionSchema.shape.prompt.maxLength);
	});

	it("interaction option label", () => {
		expect(OPTION_LABEL_MIN).toBe(SlideDeckInteractionOptionSchema.shape.label.minLength);
		expect(OPTION_LABEL_MAX).toBe(SlideDeckInteractionOptionSchema.shape.label.maxLength);
	});

	it("teacher-only rationale", () => {
		expect(RATIONALE_MIN).toBe(SlideDeckInteractionTeacherOnlySchema.shape.rationale.minLength);
		expect(RATIONALE_MAX).toBe(SlideDeckInteractionTeacherOnlySchema.shape.rationale.maxLength);
	});
});

describe("clampOrReject", () => {
	it("accepts and trims text within bounds", () => {
		const result = clampOrReject("  hello  ", 1, 10);
		expect(result).toEqual({ ok: true, value: "hello" });
	});

	it("rejects empty/whitespace-only text", () => {
		expect(clampOrReject("   ", 1, 10)).toEqual({ ok: false });
	});

	it("clamps text longer than the max to the max length", () => {
		const result = clampOrReject("x".repeat(20), 1, 10);
		expect(result.ok).toBe(true);
		expect(result.ok && result.value).toHaveLength(10);
	});

	it("never interprets input as markup — it is always returned as literal text", () => {
		const html = "<img src=x onerror=alert(1)>";
		const result = clampOrReject(html, 1, 2000);
		expect(result).toEqual({ ok: true, value: html });
	});
});
