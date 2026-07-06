import type {
  SlideDeckBlock,
  SlideDeckData,
  SlideDeckInteraction,
  SlideDeckSlide,
} from "./contracts/index.js";
import type { SlideDeckInteractionOption, SlideDeckTeacherOnly } from "./contracts/slide_deck.js";

export type SlideDeckRenderSurface = "student" | "teacher" | "print";

export type ProjectedSlideDeckOption = Readonly<{
  optionId: string;
  label: string;
  correct: boolean;
}>;

export type ProjectedSlideDeckInteraction = Readonly<{
  interactionId: string;
  interactionType: SlideDeckInteraction["interaction_type"];
  prompt: string;
  options: readonly ProjectedSlideDeckOption[];
  rationale: string;
  acceptableAnswers: readonly string[];
  noJsFallback: string;
  accessibilityLabel: string;
}>;

export type ProjectedSlideDeckBlock = Readonly<{
  blockId: string;
  blockType: SlideDeckBlock["block_type"];
  body: string;
  mediaAltText: string;
  requiresNetwork: boolean;
  fallbackText: string;
}>;

export type ProjectedSlideDeckSlide = Readonly<{
  slideId: string;
  title: string;
  layout: SlideDeckSlide["layout"];
  revealPolicy: SlideDeckSlide["progression"]["reveal_policy"];
  blocks: readonly ProjectedSlideDeckBlock[];
  interactions: readonly ProjectedSlideDeckInteraction[];
  facilitationNotes: readonly string[];
  answerKeyNotes: readonly string[];
}>;

export type ProjectedSlideDeck = Readonly<{
  title: string;
  theme?: string;
  lang: string;
  surface: SlideDeckRenderSurface;
  surfaceLabel: string;
  slides: readonly ProjectedSlideDeckSlide[];
  forbiddenStudentText: readonly string[];
  diagnostics: readonly string[];
}>;

type SlideDeckRenderInput = SlideDeckData & Readonly<{
  render_surface?: SlideDeckRenderSurface;
}>;

export function projectSlideDeckSurface(deck: SlideDeckRenderInput): ProjectedSlideDeck {
  const surface = deck.render_surface ?? "student";
  switch (surface) {
    case "student":
      return projectStudentDeck(deck);
    case "teacher":
      return projectTeacherDeck(deck);
    case "print":
      return projectPrintDeck(deck);
  }
}

export function assertStudentSlideDeckHtmlIsSafe(projected: ProjectedSlideDeck, html: string): void {
  if (projected.surface !== "student") return;
  const staticForbidden = ["teacher_only", "teacher_notes", "correct_option_ids", "acceptable_answers"];
  const leaked = [...staticForbidden, ...projected.forbiddenStudentText]
    .filter((value) => value.length > 0 && html.includes(value));
  if (leaked.length === 0) return;
  throw new SlideDeckStudentLeakError(leaked[0]);
}

export class SlideDeckStudentLeakError extends Error {
  readonly leakedText: string;

  constructor(leakedText: string) {
    super(`Student slide deck HTML leaked teacher-only data: ${leakedText}`);
    this.name = "SlideDeckStudentLeakError";
    this.leakedText = leakedText;
  }
}

function projectStudentDeck(deck: SlideDeckRenderInput): ProjectedSlideDeck {
  return {
    title: deck.title,
    theme: deck.theme,
    lang: deck.accessibility.language,
    surface: "student",
    surfaceLabel: "Student presentation",
    slides: deck.slides.map((slide) => ({
      slideId: slide.slide_id,
      title: slide.title,
      layout: slide.layout,
      revealPolicy: slide.progression.reveal_policy,
      blocks: projectBlocks(slide.blocks),
      interactions: projectStudentInteractions(slide.interactions ?? []),
      facilitationNotes: [],
      answerKeyNotes: [],
    })),
    forbiddenStudentText: forbiddenStudentText(deck),
    diagnostics: ["surface:student", "projection:teacher-only-stripped"],
  };
}

function projectTeacherDeck(deck: SlideDeckRenderInput): ProjectedSlideDeck {
  return {
    title: deck.title,
    theme: deck.theme,
    lang: deck.accessibility.language,
    surface: "teacher",
    surfaceLabel: "Teacher guide",
    slides: deck.slides.map((slide) => ({
      slideId: slide.slide_id,
      title: slide.title,
      layout: slide.layout,
      revealPolicy: slide.progression.reveal_policy,
      blocks: projectBlocks(slide.blocks),
      interactions: projectTeacherInteractions(slide.interactions ?? []),
      facilitationNotes: teacherNotes(slide.teacher_notes).facilitationNotes,
      answerKeyNotes: teacherNotes(slide.teacher_notes).answerKeyNotes,
    })),
    forbiddenStudentText: [],
    diagnostics: ["surface:teacher", "projection:teacher-guidance-visible"],
  };
}

function projectPrintDeck(deck: SlideDeckRenderInput): ProjectedSlideDeck {
  return {
    title: deck.title,
    theme: deck.theme,
    lang: deck.accessibility.language,
    surface: "print",
    surfaceLabel: "Print handout",
    slides: deck.slides.map((slide) => ({
      slideId: slide.slide_id,
      title: slide.title,
      layout: slide.layout,
      revealPolicy: "all_at_once",
      blocks: projectBlocks(slide.blocks),
      interactions: projectStudentInteractions(slide.interactions ?? []),
      facilitationNotes: [],
      answerKeyNotes: [],
    })),
    forbiddenStudentText: [],
    diagnostics: ["surface:print", "projection:reveals-expanded"],
  };
}

function projectBlocks(blocks: readonly SlideDeckBlock[]): readonly ProjectedSlideDeckBlock[] {
  return blocks.map((block) => ({
    blockId: block.block_id,
    blockType: block.block_type,
    body: block.body,
    mediaAltText: block.media?.alt_text ?? "",
    requiresNetwork: block.media?.requires_network ?? false,
    fallbackText: block.media?.fallback_text ?? "",
  }));
}

function projectStudentInteractions(interactions: readonly SlideDeckInteraction[]): readonly ProjectedSlideDeckInteraction[] {
  return interactions.map((interaction) => ({
    interactionId: interaction.interaction_id,
    interactionType: interaction.interaction_type,
    prompt: interaction.prompt,
    options: projectOptions(interaction.options ?? [], []),
    rationale: "",
    acceptableAnswers: [],
    noJsFallback: interaction.no_js_fallback ?? "Use this prompt without storing student responses.",
    accessibilityLabel: interaction.accessibility_label ?? "Slide interaction",
  }));
}

function projectTeacherInteractions(interactions: readonly SlideDeckInteraction[]): readonly ProjectedSlideDeckInteraction[] {
  return interactions.map((interaction) => ({
    interactionId: interaction.interaction_id,
    interactionType: interaction.interaction_type,
    prompt: interaction.prompt,
    options: projectOptions(interaction.options ?? [], interaction.teacher_only?.correct_option_ids ?? []),
    rationale: interaction.teacher_only?.rationale ?? "",
    acceptableAnswers: interaction.teacher_only?.acceptable_answers ?? [],
    noJsFallback: interaction.no_js_fallback ?? "Use this prompt without storing student responses.",
    accessibilityLabel: interaction.accessibility_label ?? "Slide interaction",
  }));
}

function projectOptions(
  options: readonly SlideDeckInteractionOption[],
  correctOptionIds: readonly string[],
): readonly ProjectedSlideDeckOption[] {
  return options.map((option) => ({
    optionId: option.option_id,
    label: option.label,
    correct: correctOptionIds.includes(option.option_id),
  }));
}

function teacherNotes(notes: SlideDeckTeacherOnly | null | undefined): Pick<ProjectedSlideDeckSlide, "facilitationNotes" | "answerKeyNotes"> {
  return {
    facilitationNotes: notes?.facilitation_notes ?? [],
    answerKeyNotes: notes?.answer_key_notes ?? [],
  };
}

function forbiddenStudentText(deck: SlideDeckRenderInput): readonly string[] {
  return deck.slides.flatMap((slide) => [
    ...(slide.teacher_notes?.facilitation_notes ?? []),
    ...(slide.teacher_notes?.answer_key_notes ?? []),
    ...(slide.interactions ?? []).flatMap((interaction) => [
      ...(interaction.teacher_only?.acceptable_answers ?? []),
      interaction.teacher_only?.rationale ?? "",
    ]),
  ]);
}
