export type SlideDeckSurfaceMode = "presentation" | "teacher_guide" | "print";
export type SlideDeckExportFormat = "html";
// Existing production layouts (SDE-01) plus the ADR-041 target vocabulary
// declared now (SDE-02). Renderer template support ships incrementally —
// see `RENDERER_SUPPORTED_SLIDE_LAYOUTS` in slide-deck-projection.ts, which
// fails closed for any layout without a template rather than falling back.
export type SlideDeckLayout =
  | "title" | "content" | "question" | "activity" | "summary"
  | "cover" | "agenda" | "objective" | "hook" | "concept" | "definition"
  | "comparison" | "timeline" | "process" | "diagram" | "worked_example"
  | "guided_practice" | "independent_practice" | "discussion" | "poll"
  | "quiz_check" | "reflection" | "exit_ticket" | "homework" | "appendix";
// ADR-045: pedagogical role is a slide's teaching purpose, kept separate
// from `SlideDeckLayout` (its visual shape). Mirrors
// `common.contracts.slide_deck.PedagogicalRole` (Python).
export type SlideDeckPedagogicalRole =
  | "hook" | "objective" | "explain" | "model" | "guided_practice"
  | "check_understanding" | "independent_practice" | "recap" | "exit_ticket";
export type SlideDeckBlockType = "heading" | "paragraph" | "image" | "diagram" | "callout" | "interaction_prompt";
export type SlideDeckRevealPolicy = "all_at_once" | "progressive" | "teacher_controlled";
export type SlideDeckInteractionType = "reveal" | "quick_check" | "multiple_choice_single" | "multiple_choice_multiple" | "true_false" | "short_answer" | "poll" | "poll_prompt" | "timer" | "discussion_prompt" | "exit_ticket" | "think_pair_share";
export type SlideDeckSourceConfidence = "verified" | "modified" | "uncertain";
export type SlideDeckMediaType = "image" | "audio" | "video" | "diagram";
export type SlideDeckMediaTier = "packaged" | "online_optional";

export type SlideDeckSurface = Readonly<{
  mode: SlideDeckSurfaceMode;
  export_format: SlideDeckExportFormat;
}>;

export type SlideDeckSurfaces = Readonly<{
  student: SlideDeckSurface;
  teacher: SlideDeckSurface;
  print: SlideDeckSurface;
}>;

export type SlideDeckSourceRef = Readonly<{
  source_id: string;
  title: string;
  citation: string;
  confidence: SlideDeckSourceConfidence;
}>;

export type SlideDeckProgression = Readonly<{
  step_index: number;
  reveal_policy: SlideDeckRevealPolicy;
}>;

export type SlideDeckMedia = Readonly<{
  media_id: string;
  media_type: SlideDeckMediaType;
  source: string;
  tier: SlideDeckMediaTier;
  alt_text: string;
  fallback_text?: string | null;
  requires_network?: boolean;
}>;

// ADR-045 (SDTF-03): related-artifact references are pointers, not embedded
// content -- reuses the CoreArtifactType artifact_id vocabulary the
// generation pipeline already uses (common.contracts.artifact_workflow),
// extended with "objective"/"checkpoint" semantic targets. Only
// relationship_label is ever safe to show students; artifact_type/
// artifact_id are teacher-preview planning context (see
// slide-deck-projection.ts).
export type SlideDeckRelatedArtifactType =
  | "lesson" | "worksheet" | "quiz" | "drill" | "recap" | "flashcard_deck" | "answer_key" | "roadmap" | "slide_deck"
  | "objective" | "checkpoint";

export type SlideDeckRelatedArtifactRef = Readonly<{
  artifact_type: SlideDeckRelatedArtifactType;
  artifact_id: string;
  relationship_label: string;
}>;

export type SlideDeckBlock = Readonly<{
  block_id: string;
  block_type: SlideDeckBlockType;
  body: string;
  source_ref_ids?: readonly string[];
  media?: SlideDeckMedia | null;
  related_refs?: readonly SlideDeckRelatedArtifactRef[];
}>;

export type SlideDeckInteractionOption = Readonly<{
  option_id: string;
  label: string;
}>;

export type SlideDeckInteractionTeacherOnly = Readonly<{
  separation: "teacher_only_projection";
  correct_option_ids?: readonly string[];
  acceptable_answers?: readonly string[];
  rationale: string;
}>;

export type SlideDeckInteraction = Readonly<{
  interaction_id: string;
  interaction_type: SlideDeckInteractionType;
  prompt: string;
  answer_bearing?: boolean;
  options?: readonly SlideDeckInteractionOption[];
  teacher_only?: SlideDeckInteractionTeacherOnly | null;
  no_js_fallback?: string;
  accessibility_label?: string;
}>; 

export type SlideDeckTeacherOnly = Readonly<{
  facilitation_notes?: readonly string[];
  answer_key_notes?: readonly string[];
}>;

// ADR-045 (SDTF-05): teacher-only scaffold/stretch guidance, kept separate
// from `SlideDeckTeacherOnly` (answer keys). `level` is a plain string (not
// a fixed union) so a future group/level variant is just another list item.
// Mirrors `common.contracts.slide_deck.SlideDeckDifferentiationNote` (Python).
export type SlideDeckDifferentiationNote = Readonly<{
  level: string;
  guidance: string;
}>;

export type SlideDeckSlide = Readonly<{
  slide_id: string;
  title: string;
  layout: SlideDeckLayout;
  progression: SlideDeckProgression;
  blocks: readonly SlideDeckBlock[];
  interactions?: readonly SlideDeckInteraction[];
  teacher_notes?: SlideDeckTeacherOnly | null;
  related_refs?: readonly SlideDeckRelatedArtifactRef[];
  pedagogical_role?: SlideDeckPedagogicalRole | null;
  planned_duration_minutes?: number | null;
  differentiation_guidance?: readonly SlideDeckDifferentiationNote[];
}>;

export type SlideDeckAccessibility = Readonly<{
  reading_level: string;
  language: string;
  alt_text_required: boolean;
  keyboard_navigation: boolean;
}>;

export type SlideDeckMediaPolicy = Readonly<{
  default_tier: SlideDeckMediaTier;
  online_optional_allowed: boolean;
  fallback_required: boolean;
}>;

// ADR-043: display preferences are slide-deck-specific and never LLM-authored.
export type SlideDeckDisplaySurface = "presentation" | "student" | "teacher" | "print" | "review";
export type SlideDeckPrintLayout = "paged" | "continuous";
export type SlideDeckSlidesPerPage = 1 | 2 | 4 | 6;
export type SlideDeckChromeVisibility = "hidden" | "minimal" | "branded";

export type SlideDeckDisplayPreferences = Readonly<{
  surface: SlideDeckDisplaySurface;
  print_layout: SlideDeckPrintLayout;
  slides_per_page: SlideDeckSlidesPerPage;
  chrome: SlideDeckChromeVisibility;
}>;

export const SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS: SlideDeckDisplayPreferences = {
  surface: "presentation",
  print_layout: "paged",
  slides_per_page: 1,
  chrome: "hidden",
};

const SLIDE_DECK_DISPLAY_SURFACES: ReadonlySet<string> = new Set(["presentation", "student", "teacher", "print", "review"]);
const SLIDE_DECK_PRINT_LAYOUTS: ReadonlySet<string> = new Set(["paged", "continuous"]);
const SLIDE_DECK_SLIDES_PER_PAGE: ReadonlySet<number> = new Set([1, 2, 4, 6]);
const SLIDE_DECK_CHROME_VISIBILITIES: ReadonlySet<string> = new Set(["hidden", "minimal", "branded"]);

/**
 * Resolve effective slide-deck display preferences from untrusted/partial
 * input: a missing field, an old artifact predating this contract, or a
 * malformed query/hash/localStorage override. Invalid values fall back to
 * the production-safe default for that field instead of throwing.
 *
 * This is the only sanctioned way to read display preferences — no code
 * should do loose `metadata.printLayout`-style string lookups elsewhere.
 */
export function resolveSlideDeckDisplayPreferences(raw: unknown): SlideDeckDisplayPreferences {
  const input = (raw && typeof raw === "object" ? raw : {}) as Partial<Record<keyof SlideDeckDisplayPreferences, unknown>>;
  const defaults = SLIDE_DECK_DISPLAY_PREFERENCE_DEFAULTS;
  return {
    surface: SLIDE_DECK_DISPLAY_SURFACES.has(input.surface as string)
      ? (input.surface as SlideDeckDisplaySurface)
      : defaults.surface,
    print_layout: SLIDE_DECK_PRINT_LAYOUTS.has(input.print_layout as string)
      ? (input.print_layout as SlideDeckPrintLayout)
      : defaults.print_layout,
    slides_per_page: SLIDE_DECK_SLIDES_PER_PAGE.has(input.slides_per_page as number)
      ? (input.slides_per_page as SlideDeckSlidesPerPage)
      : defaults.slides_per_page,
    chrome: SLIDE_DECK_CHROME_VISIBILITIES.has(input.chrome as string)
      ? (input.chrome as SlideDeckChromeVisibility)
      : defaults.chrome,
  };
}

// SDX-01: a translated deck is a remix (1:1 text substitution, no structural
// change) of its source deck's snapshot -- reuses SDTF-06's lineage model
// instead of a parallel "translated_from" field. Mirrors
// `common.contracts.slide_deck.SlideDeckSnapshotLineage` (Python).
export type SlideDeckSnapshotLineage = Readonly<{
  remix_of_snapshot_id: string | null;
}>;

export type SlideDeckData = Readonly<{
  deck_id: string;
  title: string;
  locale: string;
  theme?: string;
  surfaces: SlideDeckSurfaces;
  source_refs?: readonly SlideDeckSourceRef[];
  slides: readonly SlideDeckSlide[];
  accessibility: SlideDeckAccessibility;
  media_policy: SlideDeckMediaPolicy;
  display_preferences?: Partial<SlideDeckDisplayPreferences> | null;
  lineage?: Partial<SlideDeckSnapshotLineage> | null;
  // ADR-043: explicit surface override recognizes the full 5-value surface
  // set. `slide-deck-projection.ts`'s `normalizeRenderSurface` also maps
  // unrecognized/legacy runtime values (this crosses a Python/TS JSON
  // boundary, so it's untyped at runtime) safely instead of throwing.
  render_surface?: SlideDeckDisplaySurface;
  lang?: string;
}>;
