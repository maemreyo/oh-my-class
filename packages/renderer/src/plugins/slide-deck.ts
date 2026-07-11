import path from "node:path";
import { fileURLToPath } from "node:url";

import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";
import {
  assertStudentSlideDeckHtmlIsSafe,
  projectSlideDeckSurface,
  type ProjectedSlideDeck,
} from "../slide-deck-projection.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// pages/slide_deck.html embeds this exact script (byte-for-byte -- see the
// drift guard in __tests__/slide-deck-player-script.test.ts) inline via
// base.html's `<% if (it.pageJS) %>` branch. The registry-based render()
// pipeline enforces an inline-only asset policy that requires every inline
// <script> to be a declared, hash-verified ManagedScript
// (core/asset-policy.ts); renderArtifact() (renderer.ts's older API) never
// ran that check, so this declaration is new, not a pre-existing pass.
const SLIDE_DECK_PLAYER_SCRIPT_SHA256 = "b5ba0d07c36bc005ad4be6f532400084be96b80534d1ac56c5f354ef53908322";

// Mirrors common/component_strategy_knowledge's SlideDeckLayout vocabulary
// (packages/renderer/src/contracts/slide_deck.ts) exhaustively -- unlike
// slide-deck-projection.ts's RENDERER_SUPPORTED_SLIDE_LAYOUTS, this schema
// must accept every *declared* layout (validation), even ones with no
// template yet; projectSlideDeckSurface is what fails closed on those.
const slideDeckLayoutSchema = z.enum([
  "title", "content", "question", "activity", "summary",
  "cover", "agenda", "objective", "hook", "concept", "definition",
  "comparison", "timeline", "process", "diagram", "worked_example",
  "guided_practice", "independent_practice", "discussion", "poll",
  "quiz_check", "reflection", "exit_ticket", "homework", "appendix",
]);

const slideDeckPedagogicalRoleSchema = z.enum([
  "hook", "objective", "explain", "model", "guided_practice",
  "check_understanding", "independent_practice", "recap", "exit_ticket",
]);

const slideDeckBlockTypeSchema = z.enum([
  "heading", "paragraph", "image", "diagram", "callout", "interaction_prompt",
]);

const slideDeckRevealPolicySchema = z.enum(["all_at_once", "progressive", "teacher_controlled"]);

const slideDeckInteractionTypeSchema = z.enum([
  "reveal", "quick_check", "multiple_choice_single", "multiple_choice_multiple",
  "true_false", "short_answer", "poll", "poll_prompt", "timer",
  "discussion_prompt", "exit_ticket", "think_pair_share",
]);

const slideDeckSourceConfidenceSchema = z.enum(["verified", "modified", "uncertain"]);
const slideDeckMediaTypeSchema = z.enum(["image", "audio", "video", "diagram"]);
const slideDeckMediaTierSchema = z.enum(["packaged", "online_optional"]);
const slideDeckSurfaceModeSchema = z.enum(["presentation", "teacher_guide", "print"]);
const slideDeckRelatedArtifactTypeSchema = z.enum([
  "lesson", "worksheet", "quiz", "drill", "recap", "flashcard_deck", "answer_key", "roadmap", "slide_deck",
  "objective", "checkpoint",
]);
const slideDeckDisplaySurfaceSchema = z.enum(["presentation", "student", "teacher", "print", "review"]);
const slideDeckPrintLayoutSchema = z.enum(["paged", "continuous"]);
const slideDeckSlidesPerPageSchema = z.union([z.literal(1), z.literal(2), z.literal(4), z.literal(6)]);
const slideDeckChromeVisibilitySchema = z.enum(["hidden", "minimal", "branded"]);

const slideDeckSurfaceSchema = z.object({
  mode: slideDeckSurfaceModeSchema,
  export_format: z.literal("html"),
});

const slideDeckSurfacesSchema = z.object({
  student: slideDeckSurfaceSchema,
  teacher: slideDeckSurfaceSchema,
  print: slideDeckSurfaceSchema,
});

const slideDeckSourceRefSchema = z.object({
  source_id: z.string().min(1),
  title: z.string().min(1),
  citation: z.string().min(1),
  confidence: slideDeckSourceConfidenceSchema,
});

const slideDeckProgressionSchema = z.object({
  step_index: z.number().int(),
  reveal_policy: slideDeckRevealPolicySchema,
});

const slideDeckMediaSchema = z.object({
  media_id: z.string().min(1),
  media_type: slideDeckMediaTypeSchema,
  source: z.string().min(1),
  tier: slideDeckMediaTierSchema,
  alt_text: z.string(),
  fallback_text: z.string().nullable().optional(),
  requires_network: z.boolean().optional(),
});

const slideDeckRelatedArtifactRefSchema = z.object({
  artifact_type: slideDeckRelatedArtifactTypeSchema,
  artifact_id: z.string().min(1),
  relationship_label: z.string(),
});

const slideDeckBlockSchema = z.object({
  block_id: z.string().min(1),
  block_type: slideDeckBlockTypeSchema,
  body: z.string(),
  source_ref_ids: z.array(z.string()).optional(),
  media: slideDeckMediaSchema.nullable().optional(),
  related_refs: z.array(slideDeckRelatedArtifactRefSchema).optional(),
});

const slideDeckInteractionOptionSchema = z.object({
  option_id: z.string().min(1),
  label: z.string(),
});

const slideDeckInteractionTeacherOnlySchema = z.object({
  separation: z.literal("teacher_only_projection"),
  correct_option_ids: z.array(z.string()).optional(),
  acceptable_answers: z.array(z.string()).optional(),
  rationale: z.string(),
});

const slideDeckInteractionSchema = z.object({
  interaction_id: z.string().min(1),
  interaction_type: slideDeckInteractionTypeSchema,
  prompt: z.string(),
  answer_bearing: z.boolean().optional(),
  options: z.array(slideDeckInteractionOptionSchema).optional(),
  teacher_only: slideDeckInteractionTeacherOnlySchema.nullable().optional(),
  no_js_fallback: z.string().optional(),
  accessibility_label: z.string().optional(),
});

const slideDeckTeacherOnlySchema = z.object({
  facilitation_notes: z.array(z.string()).optional(),
  answer_key_notes: z.array(z.string()).optional(),
});

const slideDeckDifferentiationNoteSchema = z.object({
  level: z.string(),
  guidance: z.string(),
});

const slideDeckSlideSchema = z.object({
  slide_id: z.string().min(1),
  title: z.string(),
  layout: slideDeckLayoutSchema,
  progression: slideDeckProgressionSchema,
  blocks: z.array(slideDeckBlockSchema).min(1),
  interactions: z.array(slideDeckInteractionSchema).optional(),
  teacher_notes: slideDeckTeacherOnlySchema.nullable().optional(),
  related_refs: z.array(slideDeckRelatedArtifactRefSchema).optional(),
  pedagogical_role: slideDeckPedagogicalRoleSchema.nullable().optional(),
  planned_duration_minutes: z.number().nullable().optional(),
  differentiation_guidance: z.array(slideDeckDifferentiationNoteSchema).optional(),
});

const slideDeckAccessibilitySchema = z.object({
  reading_level: z.string(),
  language: z.string(),
  alt_text_required: z.boolean(),
  keyboard_navigation: z.boolean(),
});

const slideDeckMediaPolicySchema = z.object({
  default_tier: slideDeckMediaTierSchema,
  online_optional_allowed: z.boolean(),
  fallback_required: z.boolean(),
});

const slideDeckDisplayPreferencesSchema = z.object({
  surface: slideDeckDisplaySurfaceSchema,
  print_layout: slideDeckPrintLayoutSchema,
  slides_per_page: slideDeckSlidesPerPageSchema,
  chrome: slideDeckChromeVisibilitySchema,
});

const slideDeckSnapshotLineageSchema = z.object({
  remix_of_snapshot_id: z.string().nullable(),
});

const slideDeckInputSchema = z.object({
  deck_id: z.string().min(1),
  title: z.string().min(1),
  locale: z.string().min(1),
  theme: z.string().optional(),
  surfaces: slideDeckSurfacesSchema,
  source_refs: z.array(slideDeckSourceRefSchema).optional(),
  slides: z.array(slideDeckSlideSchema).min(1),
  accessibility: slideDeckAccessibilitySchema,
  media_policy: slideDeckMediaPolicySchema,
  display_preferences: slideDeckDisplayPreferencesSchema.partial().nullable().optional(),
  lineage: slideDeckSnapshotLineageSchema.partial().nullable().optional(),
  render_surface: slideDeckDisplaySurfaceSchema.optional(),
  lang: z.string().optional(),
});

type SlideDeckTemplateData = ProjectedSlideDeck;

function adaptSlideDeck(input: unknown, context: RenderContext, services: RenderServices): SlideDeckTemplateData {
  const deck = slideDeckInputSchema.parse(input);
  void context;
  void services;
  // render_surface, set on the input data itself, drives the projection --
  // not context.audience (a 2-value teacher/student gate that predates
  // ADR-043's 5-value surface vocabulary). Mirrors renderArtifact()'s
  // existing slide_deck handling in renderer.ts exactly, so registering
  // this plugin doesn't change what a given deck renders as today.
  return projectSlideDeckSurface(deck);
}

export const slideDeckPlugin: ArtifactKindPlugin<SlideDeckTemplateData> = {
  kind: "slide_deck",
  version: "0.1.0",
  templateVersion: "slide-deck-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: slideDeckInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: { version: "slide-deck-policy-v1", config: "base" },
  managedScripts: [{
    id: "slide-deck-player",
    sourcePath: path.resolve(__dirname, "../../templates/pages/slide-deck-player.js"),
    sha256: SLIDE_DECK_PLAYER_SCRIPT_SHA256,
  }],
  adapt: adaptSlideDeck,
  templatePath: () => "pages/slide_deck",
  // Defense in depth on top of the projector functions in
  // slide-deck-projection.ts (which never put teacher-only data into a
  // student-safe surface's projected object in the first place): re-checks
  // the final rendered HTML string for the same leak, exactly as
  // renderArtifact() already does for this artifact type.
  postSanitizeCheck: (html, templateData) =>
    assertStudentSlideDeckHtmlIsSafe(templateData as SlideDeckTemplateData, html),
};
