import { z } from "zod";

import type { ArtifactKindPlugin, RenderContext, RenderServices } from "../core/types.js";

const flashcardSchema = z.object({
  id: z.string().min(1),
  front: z.string().min(1),
  back: z.string().min(1),
  hint: z.string().optional(),
});

const flashcardDeckInputSchema = z.object({
  title: z.string().min(1),
  subject: z.string().min(1),
  gradeLevel: z.string().min(1),
  cards: z.array(flashcardSchema).min(1),
  theme: z.string().optional(),
  lang: z.string().optional(),
});

type FlashcardDeckInput = z.infer<typeof flashcardDeckInputSchema>;

type FlashcardDeckTemplateData = FlashcardDeckInput & {
  readonly themeCSS: string;
  readonly lang: string;
};

const flashcardDeckSanitizerPolicy = { version: "flashcard-deck-policy-v1", config: "quiz" } as const;

function adaptFlashcardDeck(input: unknown, context: RenderContext, services: RenderServices): FlashcardDeckTemplateData {
  const deck = flashcardDeckInputSchema.parse(input);
  return { ...deck, lang: deck.lang ?? context.locale, themeCSS: services.themeCss };
}

export const flashcardDeckPlugin: ArtifactKindPlugin<FlashcardDeckTemplateData> = {
  kind: "flashcard_deck",
  version: "0.1.0",
  templateVersion: "flashcard-deck-template-v1",
  themeVersion: "theme-resolver-v1",
  schema: flashcardDeckInputSchema,
  audience: { supported: ["teacher", "student"] },
  capabilities: { supportsPrint: true },
  sanitizerPolicy: flashcardDeckSanitizerPolicy,
  adapt: adaptFlashcardDeck,
  templatePath: () => "pages/flashcard_deck",
};
