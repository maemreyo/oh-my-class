export type SlideDeckSurfaceMode = "presentation" | "teacher_guide" | "print";
export type SlideDeckExportFormat = "html";
export type SlideDeckLayout = "title" | "content" | "question" | "activity" | "summary";
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

export type SlideDeckBlock = Readonly<{
  block_id: string;
  block_type: SlideDeckBlockType;
  body: string;
  source_ref_ids?: readonly string[];
  media?: SlideDeckMedia | null;
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

export type SlideDeckSlide = Readonly<{
  slide_id: string;
  title: string;
  layout: SlideDeckLayout;
  progression: SlideDeckProgression;
  blocks: readonly SlideDeckBlock[];
  interactions?: readonly SlideDeckInteraction[];
  teacher_notes?: SlideDeckTeacherOnly | null;
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
  render_surface?: "student" | "teacher" | "print";
  lang?: string;
}>;
