import { describe, expect, it } from "vitest";
import { getSlideDeckFailureCopy } from "./failure-copy";

// One representative code per AC category (SDH-11): sparse deck, quality
// gate, leakage, export/render, print, infrastructure.
const REPRESENTATIVE_CODES: Readonly<Record<string, string>> = {
	sparse_deck: "deck_shape_incomplete",
	quality_gate: "invalid_layout",
	leakage: "answer_key_leakage",
	export_render: "missing_doctype",
	print: "print_export_failed",
	infrastructure: "breaker_tripped",
};

const RAW_LEAK_MARKERS = [
	"Traceback (most recent call last)",
	"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", // JWT-shaped base64
	"correct_option_ids",
	"rationale:",
	"at Object.<anonymous>",
];

describe("getSlideDeckFailureCopy — 6 failure categories map to safe copy", () => {
	for (const [category, code] of Object.entries(REPRESENTATIVE_CODES)) {
		it(`${category} (${code}) has a category, a safe message, and an actionable next step`, () => {
			const copy = getSlideDeckFailureCopy(code);
			expect(copy.category).toBe(category);
			expect(copy.message.length).toBeGreaterThan(0);
			expect(["regenerate", "revise_prompt", "inspect_teacher_notes", "retry_export", "contact_admin"]).toContain(
				copy.nextAction,
			);
			for (const marker of RAW_LEAK_MARKERS) {
				expect(copy.message).not.toContain(marker);
			}
		});
	}
});

describe("getSlideDeckFailureCopy — recovery scope distinguishes scoped repair from full regeneration", () => {
	it("single-slide/block issues are scoped (repairing this slide)", () => {
		expect(getSlideDeckFailureCopy("invalid_block").recoveryScope).toBe("scoped");
		expect(getSlideDeckFailureCopy("missing_alt_text").recoveryScope).toBe("scoped");
		expect(getSlideDeckFailureCopy("teacher_only_leak_risk").recoveryScope).toBe("scoped");
		expect(getSlideDeckFailureCopy("answer_key_leakage").recoveryScope).toBe("scoped");
	});

	it("deck-structural issues require full regeneration", () => {
		expect(getSlideDeckFailureCopy("deck_shape_incomplete").recoveryScope).toBe("full_regeneration");
		expect(getSlideDeckFailureCopy("deck_shape_unjustified_slide").recoveryScope).toBe("full_regeneration");
		expect(getSlideDeckFailureCopy("surfaces_incomplete").recoveryScope).toBe("full_regeneration");
		expect(getSlideDeckFailureCopy("page_count_too_short").recoveryScope).toBe("full_regeneration");
	});
});

describe("getSlideDeckFailureCopy — SDE-10 editor availability (feature gate + rate limit)", () => {
	it("a disabled AI-rewrite flag maps to a scoped, teacher-safe message", () => {
		const copy = getSlideDeckFailureCopy("slide_deck_ai_rewrite_disabled");
		expect(copy.category).toBe("editor_availability");
		expect(copy.recoveryScope).toBe("scoped");
	});

	it("an exceeded rate limit maps to try_again_later, not a raw 429", () => {
		const copy = getSlideDeckFailureCopy("ai_rewrite_rate_limited");
		expect(copy.category).toBe("editor_availability");
		expect(copy.nextAction).toBe("try_again_later");
		expect(copy.message).not.toContain("429");
	});
});

describe("getSlideDeckFailureCopy — unrecognized codes never leak raw text", () => {
	it("falls back to a generic safe message for an unknown code", () => {
		const copy = getSlideDeckFailureCopy("some_future_code_nobody_mapped_yet");
		expect(copy.category).toBe("unknown");
		expect(copy.message).toBe(getSlideDeckFailureCopy("literally_anything_unrecognized").message);
	});

	it("never reflects a raw error string back, even if one is passed in place of a code", () => {
		const rawError = 'TypeError: Cannot read properties of undefined (reading "slides")\n  at generateDeck (/app/engine.js:42:11)\n  Bearer eyJhbGciOiJIUzI1NiJ9.raw.jwt';
		const copy = getSlideDeckFailureCopy(rawError);
		expect(copy.category).toBe("unknown");
		expect(copy.message).not.toContain("TypeError");
		expect(copy.message).not.toContain("engine.js");
		expect(copy.message).not.toContain("Bearer");
		expect(copy.message).not.toContain(rawError);
	});
});

describe("getSlideDeckFailureCopy — full failure table never leaks raw technical markers", () => {
	// A code isn't "recognized" by re-parsing/echoing whatever string is
	// passed in — every entry in the table is a fixed, pre-written string.
	// This guards the whole table at once instead of one code at a time.
	const allCodes = [
		"deck_shape_incomplete",
		"page_count_too_short",
		"surfaces_incomplete",
		"deck_shape_unjustified_slide",
		"page_count_exceeded",
		"html_exports_incomplete",
		"pacing_mismatch",
		"objective_coverage_gap",
		"invalid_layout",
		"invalid_block",
		"invalid_interaction",
		"missing_source_refs",
		"unsupported_media",
		"density_budget_exceeded",
		"density_purpose_gap",
		"missing_alt_text",
		"teacher_only_leak_risk",
		"answer_key_leakage",
		"pii_leakage",
		"schema_invalid",
		"missing_doctype",
		"external_assets",
		"external_asset",
		"native_radio_inputs",
		"unmanaged_js_runtime",
		"missing_brand_string",
		"contrast_below_aa",
		"broken_heading_order",
		"missing_form_label",
		"missing_lang",
		"missing_long_description",
		"teacher_gate_not_approved",
		"SlideDeckUnsupportedLayoutError",
		"print_export_failed",
		"transient",
		"tool_unavailable",
		"breaker_tripped",
		"infrastructure_error",
		"slide_deck_ai_rewrite_disabled",
		"slide_deck_editor_disabled",
		"ai_rewrite_rate_limited",
	];

	it.each(allCodes)("%s message contains no raw technical markers", (code) => {
		const copy = getSlideDeckFailureCopy(code);
		for (const marker of RAW_LEAK_MARKERS) {
			expect(copy.message).not.toContain(marker);
		}
		// No stack-trace-ish content, no "at <file>:<line>" fragments.
		expect(copy.message).not.toMatch(/\bat .+:\d+:\d+/);
		expect(copy.message).not.toMatch(/^[A-Za-z]+Error:/);
	});
});
