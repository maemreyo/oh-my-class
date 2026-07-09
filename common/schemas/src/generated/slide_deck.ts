/**
 * AUTO-GENERATED from Pydantic model_json_schema()
 * Source: common/contracts/ → Pydantic → JSON Schema → Zod
 * DO NOT EDIT MANUALLY — run `python scripts/generate_zod_schemas.py` to regenerate
 */

import { z } from "zod"

export const SlideDeckSurfacesSchema = z.object({ "student": z.lazy(() => SlideDeckSurfaceSchema), "teacher": z.lazy(() => SlideDeckSurfaceSchema), "print": z.lazy(() => SlideDeckSurfaceSchema) })


export const SlideDeckSurfaceSchema = z.object({ "mode": z.enum(["presentation","teacher_guide","print"]), "export_format": z.literal("html") })


export const SlideDeckSourceRefSchema = z.object({ "source_id": z.string().min(1).max(80), "title": z.string().min(1).max(200), "citation": z.string().min(1).max(500), "confidence": z.enum(["verified","modified","uncertain"]) })


export const SlideDeckSlideSchema = z.object({ "slide_id": z.string().min(1).max(80), "title": z.string().min(1).max(200), "layout": z.enum(["title","content","question","activity","summary","cover","agenda","objective","hook","concept","definition","comparison","timeline","process","diagram","worked_example","guided_practice","independent_practice","discussion","poll","quiz_check","reflection","exit_ticket","homework","appendix"]), "progression": z.lazy(() => SlideDeckProgressionSchema), "blocks": z.array(z.lazy(() => SlideDeckBlockSchema)).min(1), "interactions": z.array(z.lazy(() => SlideDeckInteractionSchema)).optional(), "teacher_notes": z.union([z.lazy(() => SlideDeckTeacherOnlySchema), z.null()]).default(null), "pedagogical_role": z.union([z.enum(["hook","objective","explain","model","guided_practice","check_understanding","independent_practice","recap","exit_ticket"]), z.null()]).default(null), "planned_duration_minutes": z.union([z.number().gte(0).lte(180), z.null()]).default(null), "related_refs": z.array(z.any()).optional(), "differentiation_guidance": z.array(z.lazy(() => SlideDeckDifferentiationNoteSchema)).optional() })


export const SlideDeckProgressionSchema = z.object({ "step_index": z.number().int().gte(1), "reveal_policy": z.enum(["all_at_once","progressive","teacher_controlled"]) })


export const SlideDeckBlockSchema = z.object({ "block_id": z.string().min(1).max(80), "block_type": z.enum(["heading","paragraph","image","diagram","callout","interaction_prompt"]), "body": z.string().min(1).max(2000), "source_ref_ids": z.array(z.string()).optional(), "media": z.union([z.lazy(() => SlideDeckMediaSchema), z.null()]).default(null), "related_refs": z.array(z.any()).optional() })


export const SlideDeckMediaSchema = z.object({ "media_id": z.string().min(1).max(80), "media_type": z.enum(["image","audio","video","diagram"]), "source": z.string().min(1).max(500), "tier": z.enum(["packaged","online_optional"]), "alt_text": z.string().min(1).max(500), "fallback_text": z.union([z.string().max(500), z.null()]).default(null), "requires_network": z.boolean().default(false) })


export const SlideDeckInteractionSchema = z.object({ "interaction_id": z.string().min(1).max(80), "interaction_type": z.enum(["reveal","quick_check","multiple_choice_single","multiple_choice_multiple","true_false","short_answer","poll","poll_prompt","timer","discussion_prompt","exit_ticket","think_pair_share"]), "prompt": z.string().min(1).max(1000), "answer_bearing": z.boolean().default(false), "options": z.array(z.lazy(() => SlideDeckInteractionOptionSchema)).optional(), "teacher_only": z.union([z.lazy(() => SlideDeckInteractionTeacherOnlySchema), z.null()]).default(null), "no_js_fallback": z.string().min(1).max(500).default("Use this prompt as an offline classroom discussion."), "accessibility_label": z.string().min(1).max(200).default("Slide interaction") })


export const SlideDeckInteractionOptionSchema = z.object({ "option_id": z.string().min(1).max(80), "label": z.string().min(1).max(500) })


export const SlideDeckInteractionTeacherOnlySchema = z.object({ "separation": z.literal("teacher_only_projection"), "correct_option_ids": z.array(z.string()).optional(), "acceptable_answers": z.array(z.string()).optional(), "rationale": z.string().min(1).max(1000) })


export const SlideDeckTeacherOnlySchema = z.object({ "facilitation_notes": z.array(z.string()).optional(), "answer_key_notes": z.array(z.string()).optional() })


export const SlideDeckDifferentiationNoteSchema = z.object({ "level": z.string().min(1).max(40), "guidance": z.string().min(1).max(1000) })


export const SlideDeckAccessibilitySchema = z.object({ "reading_level": z.string().min(1).max(80), "language": z.string().min(2).max(32), "alt_text_required": z.boolean().default(true), "keyboard_navigation": z.boolean().default(true) })


export const SlideDeckMediaPolicySchema = z.object({ "default_tier": z.enum(["packaged","online_optional"]), "online_optional_allowed": z.boolean(), "fallback_required": z.boolean() })


export const SlideDeckDisplayPreferencesSchema = z.object({ "surface": z.enum(["presentation","student","teacher","print","review"]).default("presentation"), "print_layout": z.enum(["paged","continuous"]).default("paged"), "slides_per_page": z.union([z.literal(1), z.literal(2), z.literal(4), z.literal(6)]).default(1), "chrome": z.enum(["hidden","minimal","branded"]).default("hidden") }).describe("Typed, slide-deck-specific display preferences (ADR-043).\n\nCovers surface, print layout, slides-per-page, and chrome visibility.\nStrict Literal fields reject invalid values at construction time. The\nLLM never populates this model — it is owned by the app, gateway\npreview/export routes, and standalone HTML. Use\n``resolve_slide_deck_display_preferences`` to safely coerce\nuntrusted/partial input (old artifacts, query/hash/localStorage\noverrides) instead of raising.")


export const SlideDeckSnapshotLineageSchema = z.object({ "remix_of_snapshot_id": z.union([z.string().min(1).max(120), z.null()]).default(null) }).describe("ADR-045 decisions 2 & 15: remix derives a new snapshot, it never\nrewrites an existing one.\n\n``remix_of_snapshot_id`` is ``None`` for an original generation and set\nto the parent snapshot's ID for a remix (\"make easier\", \"reuse slides\n3-5\", ...). This is deliberately a separate model/namespace from\n``SlideDeckDisplayPreferences``: a display/export choice (surface,\nprint layout, slides-per-page, chrome) never creates a content version\nand must never be read as lineage, and lineage must never be read as a\ndisplay preference. There is no remix API or patch-application engine\nyet -- SDE-04..06 build that runtime.")


export const SlideDeckDataSchema = z.object({ "deck_id": z.string().min(1).max(80), "title": z.string().min(3).max(200), "locale": z.string().min(2).max(16), "theme": z.string().min(1).max(80).default("default"), "surfaces": z.lazy(() => SlideDeckSurfacesSchema), "source_refs": z.array(z.lazy(() => SlideDeckSourceRefSchema)).optional(), "slides": z.array(z.lazy(() => SlideDeckSlideSchema)).min(1), "accessibility": z.lazy(() => SlideDeckAccessibilitySchema), "media_policy": z.lazy(() => SlideDeckMediaPolicySchema), "display_preferences": z.union([z.lazy(() => SlideDeckDisplayPreferencesSchema), z.null()]).default(null), "lineage": z.union([z.lazy(() => SlideDeckSnapshotLineageSchema), z.null()]).default(null) }).describe("Canonical data model for one native slide deck artifact.")

export type SlideDeckData = z.infer<typeof SlideDeckDataSchema>;
export type SlideDeckSurfaces = z.infer<typeof SlideDeckSurfacesSchema>;
export type SlideDeckSurface = z.infer<typeof SlideDeckSurfaceSchema>;
export type SlideDeckSourceRef = z.infer<typeof SlideDeckSourceRefSchema>;
export type SlideDeckSlide = z.infer<typeof SlideDeckSlideSchema>;
export type SlideDeckProgression = z.infer<typeof SlideDeckProgressionSchema>;
export type SlideDeckBlock = z.infer<typeof SlideDeckBlockSchema>;
export type SlideDeckMedia = z.infer<typeof SlideDeckMediaSchema>;
export type SlideDeckInteraction = z.infer<typeof SlideDeckInteractionSchema>;
export type SlideDeckInteractionOption = z.infer<typeof SlideDeckInteractionOptionSchema>;
export type SlideDeckInteractionTeacherOnly = z.infer<typeof SlideDeckInteractionTeacherOnlySchema>;
export type SlideDeckTeacherOnly = z.infer<typeof SlideDeckTeacherOnlySchema>;
export type SlideDeckDifferentiationNote = z.infer<typeof SlideDeckDifferentiationNoteSchema>;
export type SlideDeckAccessibility = z.infer<typeof SlideDeckAccessibilitySchema>;
export type SlideDeckMediaPolicy = z.infer<typeof SlideDeckMediaPolicySchema>;
export type SlideDeckDisplayPreferences = z.infer<typeof SlideDeckDisplayPreferencesSchema>;
export type SlideDeckSnapshotLineage = z.infer<typeof SlideDeckSnapshotLineageSchema>;
