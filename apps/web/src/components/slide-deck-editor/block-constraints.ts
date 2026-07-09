/**
 * Field-level edit policy for the slide deck editor (SDE-03).
 *
 * Bounds mirror the pydantic `Field(...)` constraints in
 * `common/contracts/slide_deck.py` (`SlideDeckBlock.body`,
 * `SlideDeckMedia.alt_text`, `SlideDeckInteraction.prompt`,
 * `SlideDeckInteractionOption.label`, `SlideDeckInteractionTeacherOnly.rationale`).
 *
 * They are hardcoded here rather than introspected from the generated Zod
 * schemas at runtime: `@oh-my-class/schemas` ships its TS source directly
 * (package.json "exports" points at src/index.ts, no dist build) with
 * NodeNext-style ".js" relative imports between its own files. Turbopack
 * does not resolve that extension-remapping for a *value* import of an
 * untranspiled workspace package (`import type` is fine — it's erased before
 * bundling, which is why every other file in this editor only type-imports
 * from that package). `block-constraints.test.ts` cross-checks these numbers
 * against the real generated schema so they can't silently drift — that
 * check runs under vitest, which resolves the package's TS source natively
 * and never hits the Turbopack limitation.
 *
 * `clampOrReject` is the one place every block/interaction editor commits a
 * text edit through: too-short (including empty) input is rejected (the
 * original value is kept), too-long input is clamped to the max. This is the
 * enforcement point for SDE-03's "no raw HTML acceptance path" acceptance
 * criterion — every field is a plain string bounded by these limits, never
 * markup.
 */
export const BLOCK_BODY_MIN = 1;
export const BLOCK_BODY_MAX = 2000;

export const MEDIA_ALT_TEXT_MIN = 1;
export const MEDIA_ALT_TEXT_MAX = 500;

export const INTERACTION_PROMPT_MIN = 1;
export const INTERACTION_PROMPT_MAX = 1000;

export const OPTION_LABEL_MIN = 1;
export const OPTION_LABEL_MAX = 500;

export const RATIONALE_MIN = 1;
export const RATIONALE_MAX = 1000;

export type FieldEditResult = { readonly ok: true; readonly value: string } | { readonly ok: false };

/** Trim, reject below `min` (reverts the caller to the previous value), clamp above `max`. */
export function clampOrReject(draft: string, min: number, max: number): FieldEditResult {
	const trimmed = draft.trim();
	if (trimmed.length < min) return { ok: false };
	return { ok: true, value: trimmed.length > max ? trimmed.slice(0, max) : trimmed };
}
