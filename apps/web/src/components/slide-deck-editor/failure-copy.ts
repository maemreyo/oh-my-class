/**
 * Teacher-safe slide-deck failure copy (SDH-11).
 *
 * Maps the *existing* backend failure classification codes to pre-written,
 * safe teacher-facing copy — never the backend's own message/error text.
 * Sources for the codes below (don't invent parallel ones, read from these):
 *   - `packages/agents/slide_deck_engine/models.py` — `SlideDeckValidationCode`
 *     (density/layout/block/teacher-only-leak/deck-shape checks).
 *   - `packages/agents/slide_deck_engine/quality.py`'s `_healing_for` — the
 *     ground truth for each code's `SlideDeckHealingScope` ("block"/"slide"
 *     mean a single-slide repair is possible; "plan"/"deck" mean the whole
 *     deck's structure has to be replanned).
 *   - `packages/quality/compliance_policy.py`'s `COMPLIANCE_HARD_BLOCK_CODES`
 *     and `packages/agents/teaching_pack/compliance.py`'s violation codes
 *     (leakage + export/render hard blocks; always routes to
 *     `quality_recovery_route: "artifact_workflow"`, i.e. a scoped retry).
 *   - `packages/renderer/src/slide-deck-projection.ts`'s
 *     `SlideDeckUnsupportedLayoutError` (`.name`), thrown by
 *     `assertSlideLayoutsAreRenderable` for any surface including print.
 *   - `packages/agents/events.py` / `tools/fs.py` / `healing/orchestrator.py`
 *     for the generic infra signal names (`breaker_tripped`,
 *     `tool_unavailable`, `transient`) — these aren't slide-deck-specific,
 *     there is no finer-grained code for infra/print failures today.
 *
 * `print_export_failed` and `infrastructure_error` are the two labels here
 * with no backend enum member yet (print and infra don't have per-cause
 * codes in this codebase). They exist only as the safe fallback for those
 * two categories; ponytail: replace with real codes once the print-export
 * pipeline and generic infra layer start emitting one.
 */

export type SlideDeckFailureCategory =
	| "sparse_deck"
	| "quality_gate"
	| "leakage"
	| "export_render"
	| "print"
	| "infrastructure"
	| "unknown";

export type SlideDeckFailureNextAction =
	| "regenerate"
	| "revise_prompt"
	| "inspect_teacher_notes"
	| "retry_export"
	| "contact_admin";

export type SlideDeckFailureRecoveryScope = "scoped" | "full_regeneration";

export interface SlideDeckFailureCopy {
	readonly category: SlideDeckFailureCategory;
	/** Pre-written, teacher-safe copy. Never interpolates raw error/model text. */
	readonly message: string;
	readonly nextAction: SlideDeckFailureNextAction;
	/** "scoped" = repairing this slide/block; "full_regeneration" = the whole deck. */
	readonly recoveryScope: SlideDeckFailureRecoveryScope;
}

const UNKNOWN_FAILURE: SlideDeckFailureCopy = {
	category: "unknown",
	message: "Something went wrong while working on this deck. Please try again, and contact support if it continues.",
	nextAction: "contact_admin",
	recoveryScope: "full_regeneration",
};

const FAILURE_COPY: Readonly<Record<string, SlideDeckFailureCopy>> = {
	// -- sparse deck (SDH-06 deck_shape / page_count / surfaces, deck-scoped) --
	deck_shape_incomplete: {
		category: "sparse_deck",
		message: "This deck is missing required parts of the lesson (like the hook, objective, or exit ticket). We'll regenerate the full deck to restore the required structure.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	page_count_too_short: {
		category: "sparse_deck",
		message: "This deck came out shorter than a full lesson needs. We'll regenerate the full deck with complete coverage.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	surfaces_incomplete: {
		category: "sparse_deck",
		message: "The student, teacher, and print versions of this deck aren't all ready yet. We'll regenerate the full deck so every view is complete.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},

	// -- quality gate (deck-level structural issues stay full_regeneration; --
	// -- single-slide/block issues are scoped, per `_healing_for`'s scope) --
	deck_shape_unjustified_slide: {
		category: "quality_gate",
		message: "This deck added more slides than the topic, duration, or grade level justifies. We'll regenerate the full deck to bring it back in line.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	page_count_exceeded: {
		category: "quality_gate",
		message: "This deck grew longer than a single lesson should be. We'll regenerate the full deck at the right length.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	html_exports_incomplete: {
		category: "quality_gate",
		message: "This deck isn't ready to export in every format yet. We'll regenerate the full deck.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	pacing_mismatch: {
		category: "quality_gate",
		message: "This deck's slide order doesn't match its lesson plan. We'll regenerate the full deck to fix the sequencing.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},
	objective_coverage_gap: {
		category: "quality_gate",
		message: "This deck doesn't fully cover its planned learning objective. Try revising the topic or objective details, then we'll regenerate the full deck.",
		nextAction: "revise_prompt",
		recoveryScope: "full_regeneration",
	},
	invalid_layout: {
		category: "quality_gate",
		message: "One slide uses a layout we can't render yet. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	invalid_block: {
		category: "quality_gate",
		message: "One slide has a content block we don't support yet. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	invalid_interaction: {
		category: "quality_gate",
		message: "One slide has an interaction type we don't support yet. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	missing_source_refs: {
		category: "quality_gate",
		message: "One slide is missing a required source reference. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	unsupported_media: {
		category: "quality_gate",
		message: "One slide includes media that isn't safe to show offline. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	density_budget_exceeded: {
		category: "quality_gate",
		message: "One slide has more content than fits on a presentation slide. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	density_purpose_gap: {
		category: "quality_gate",
		message: "One slide doesn't yet have the content its place in the lesson needs. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	missing_alt_text: {
		category: "quality_gate",
		message: "One slide is missing image descriptions needed for accessibility. We're repairing just that slide.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},

	// -- leakage (answer-key / PII / teacher-only separation hard blocks) --
	teacher_only_leak_risk: {
		category: "leakage",
		message: "We caught an answer that wasn't properly separated from the student view on one slide. We're repairing just that slide before it can be shared.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	answer_key_leakage: {
		category: "leakage",
		message: "We blocked this deck because answer-key content showed up where students could see it. Check the teacher notes, then we'll regenerate the affected content.",
		nextAction: "inspect_teacher_notes",
		recoveryScope: "scoped",
	},
	pii_leakage: {
		category: "leakage",
		message: "We blocked this deck because it contained personal information that shouldn't be shared. Check the teacher notes, then we'll regenerate the affected content.",
		nextAction: "inspect_teacher_notes",
		recoveryScope: "scoped",
	},

	// -- export/render (compliance hard blocks on the rendered HTML; always --
	// -- routes to a scoped `artifact_workflow` retry in compliance_gate_state) --
	schema_invalid: {
		category: "export_render",
		message: "This export didn't meet our content-safety format. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	missing_doctype: {
		category: "export_render",
		message: "The exported page is missing required structure. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	external_assets: {
		category: "export_render",
		message: "The export tried to load something from outside the app, which isn't allowed offline. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	external_asset: {
		category: "export_render",
		message: "The export tried to load something from outside the app, which isn't allowed offline. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	native_radio_inputs: {
		category: "export_render",
		message: "The export used an unsupported input type. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	unmanaged_js_runtime: {
		category: "export_render",
		message: "The export tried to load code we don't allow. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	missing_brand_string: {
		category: "export_render",
		message: "The export is missing required branding. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	contrast_below_aa: {
		category: "export_render",
		message: "Some text in this export doesn't meet accessibility contrast requirements. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	broken_heading_order: {
		category: "export_render",
		message: "The export's heading structure needs fixing for accessibility. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	missing_form_label: {
		category: "export_render",
		message: "An interactive element in this export is missing an accessible label. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	missing_lang: {
		category: "export_render",
		message: "The export is missing a required language setting. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	missing_long_description: {
		category: "export_render",
		message: "An image or diagram in this export needs a longer description for accessibility. Try exporting again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},
	teacher_gate_not_approved: {
		category: "export_render",
		message: "This deck is waiting for teacher approval before it can be shared or exported.",
		nextAction: "inspect_teacher_notes",
		recoveryScope: "scoped",
	},
	// `SlideDeckUnsupportedLayoutError.name` from packages/renderer/src/slide-deck-projection.ts.
	SlideDeckUnsupportedLayoutError: {
		category: "export_render",
		message: "One slide uses a layout with no renderer yet. We'll regenerate the full deck with a supported layout.",
		nextAction: "regenerate",
		recoveryScope: "full_regeneration",
	},

	// -- print (same rendering pipeline as export_render, no finer backend --
	// -- code for the print surface specifically yet) --
	print_export_failed: {
		category: "print",
		message: "The printable handout for this deck couldn't be generated. Try exporting the print version again.",
		nextAction: "retry_export",
		recoveryScope: "scoped",
	},

	// -- infrastructure (generic pipeline signals, not slide-deck-specific) --
	transient: {
		category: "infrastructure",
		message: "A temporary issue interrupted this step. Try again in a moment.",
		nextAction: "regenerate",
		recoveryScope: "scoped",
	},
	tool_unavailable: {
		category: "infrastructure",
		message: "A required system service is temporarily unavailable. If this continues, contact your administrator.",
		nextAction: "contact_admin",
		recoveryScope: "full_regeneration",
	},
	breaker_tripped: {
		category: "infrastructure",
		message: "This step is temporarily paused after repeated failures, to protect your content. Please try again later or contact your administrator.",
		nextAction: "contact_admin",
		recoveryScope: "full_regeneration",
	},
	infrastructure_error: {
		category: "infrastructure",
		message: "Something went wrong on our end. Please try again, and contact support if it continues.",
		nextAction: "contact_admin",
		recoveryScope: "full_regeneration",
	},
};

/**
 * Look up teacher-safe copy for a slide-deck failure classification code.
 *
 * Takes only the `code` — deliberately no raw-error/message parameter, so
 * there is no path through which raw model output, stack traces, or debug
 * text can reach the returned copy, even if a caller mistakenly passes a
 * raw error string in place of a real code: an unrecognized string always
 * falls back to `UNKNOWN_FAILURE`'s generic, pre-written message.
 */
export function getSlideDeckFailureCopy(code: string): SlideDeckFailureCopy {
	return FAILURE_COPY[code] ?? UNKNOWN_FAILURE;
}
