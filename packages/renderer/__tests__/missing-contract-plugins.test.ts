import { describe, expect, it } from "vitest";

import { render, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";

const flashcardDeckInput = {
  title: "Fraction Flashcards",
  subject: "Math",
  gradeLevel: "Grade 5",
  cards: [
    { id: "f1", front: "Equivalent", back: "Equal in value", hint: "Think same amount" },
    { id: "f2", front: "1/2", back: "2/4" },
  ],
} as const;

const readingPassageInput = {
  title: "Garden Fractions",
  subject: "Math",
  gradeLevel: "Grade 5",
  passage: "Mina planted half of a garden with beans.\n\nLater, she noticed two fourths of the garden were beans too.",
  questions: [
    { id: "rp1", prompt: "What fraction matched one half?", answer: "SECRET_READING_SHORT_ANSWER", type: "short_answer" },
    { id: "rp2", prompt: "Choose the equivalent fraction.", answer: "SECRET_READING_MC_ANSWER", type: "mc", options: [{ label: "A", text: "2/4" }, { label: "B", text: "3/5" }] },
  ],
} as const;

const exitTicketInput = {
  title: "Fraction Exit Ticket",
  subject: "Math",
  gradeLevel: "Grade 5",
  questions: [
    { id: "et1", prompt: "1/2 = __/4", type: "short_answer" },
    { id: "et2", prompt: "How confident are you?", type: "rating" },
    { id: "et3", prompt: "Pick an equivalent fraction.", type: "mc", options: [{ label: "A", text: "2/4" }, { label: "B", text: "2/5" }] },
  ],
} as const;

const roadmapInput = {
  title: "Fraction Roadmap",
  hero: {
    eyebrow: "Personal path",
    title: "Master equivalent fractions",
    lede: "Move from visual models to symbolic reasoning.",
    stamp: "READY",
    stats: [{ label: "Target", value: "Apply", variant: "target" }],
  },
  sidebar: {
    title: "Roadmap",
    subtitle: "Grade 5 Math",
    stats: [{ label: "Steps", value: "3" }],
    nav: [{ label: "Phase 1", href: "#phase-1", group: "a" }],
    legend: [{ color: "#33508F", label: "Core" }],
  },
  sections: [
    {
      id: "phase-1",
      title: "Build visual meaning",
      subtitle: "Concrete models",
      tag_num: "01",
      components: [{ type: "callout", variant: "tip", title: "Focus", body: "Use equal wholes." }],
    },
  ],
  accessibility: { language: "en" },
} as const;

function context(kind: string, renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience: "student",
    locale: "en",
    theme: "default",
    renderMode,
    requestId: `${kind}-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("missing contract artifact plugins", () => {
  it("declares registry metadata for all four missing contract kinds", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({ kind: "flashcard_deck", version: "0.1.0", templateVersion: "flashcard-deck-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "flashcard-deck-policy-v1" });
    expect(metadata).toContainEqual({ kind: "reading_passage", version: "0.1.0", templateVersion: "reading-passage-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "reading-passage-policy-v1" });
    expect(metadata).toContainEqual({ kind: "exit_ticket", version: "0.1.0", templateVersion: "exit-ticket-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "exit-ticket-policy-v1" });
    expect(metadata).toContainEqual({ kind: "roadmap", version: "0.1.0", templateVersion: "roadmap-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "roadmap-policy-v1" });
  });

  it("renders flashcard_deck standalone HTML with a manifest", async () => {
    const response = await render({ kind: "flashcard_deck", input: flashcardDeckInput, context: context("flashcard_deck", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fraction Flashcards");
    expect(response.html).toContain("Equal in value");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("flashcard_deck");
    expect(response.html).toMatchSnapshot("flashcard-deck-student-preview");
  });

  it("renders reading_passage without answer leakage", async () => {
    const response = await render({ kind: "reading_passage", input: readingPassageInput, context: context("reading_passage", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Garden Fractions");
    expect(response.html).toContain("What fraction matched one half?");
    expect(response.html).not.toContain("SECRET_READING_SHORT_ANSWER");
    expect(response.html).not.toContain("SECRET_READING_MC_ANSWER");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("reading_passage");
    expect(response.html).toMatchSnapshot("reading-passage-student-preview");
  });

  it("renders exit_ticket standalone HTML with a manifest", async () => {
    const response = await render({ kind: "exit_ticket", input: exitTicketInput, context: context("exit_ticket", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fraction Exit Ticket");
    expect(response.html).toContain("How confident are you?");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("exit_ticket");
    expect(response.html).toMatchSnapshot("exit-ticket-student-preview");
  });

  it("renders roadmap standalone HTML with a manifest", async () => {
    const response = await render({ kind: "roadmap", input: roadmapInput, context: context("roadmap", "preview") });

    expect(response.html).toMatch(/^<!DOCTYPE html>/);
    expect(response.html).toContain("Fraction Roadmap");
    expect(response.html).toContain("Build visual meaning");
    expect(response.html).not.toMatch(/https?:\/\//);
    expect(response.manifest.kind).toBe("roadmap");
    expect(response.html).toMatchSnapshot("roadmap-student-preview");
  });

  it("supports print mode for all four missing contract plugins", async () => {
    const responses = await Promise.all([
      render({ kind: "flashcard_deck", input: flashcardDeckInput, context: context("flashcard_deck", "print") }),
      render({ kind: "reading_passage", input: readingPassageInput, context: context("reading_passage", "print") }),
      render({ kind: "exit_ticket", input: exitTicketInput, context: context("exit_ticket", "print") }),
      render({ kind: "roadmap", input: roadmapInput, context: context("roadmap", "print") }),
    ]);

    expect(responses.every((response) => response.html.includes("@media print"))).toBe(true);
  });

  it("rejects invalid missing contract inputs before rendering", async () => {
    await expect(render({ kind: "flashcard_deck", input: { ...flashcardDeckInput, cards: [] }, context: context("flashcard_deck", "preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "reading_passage", input: { ...readingPassageInput, questions: [] }, context: context("reading_passage", "preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "exit_ticket", input: { ...exitTicketInput, questions: [] }, context: context("exit_ticket", "preview") })).rejects.toThrow(/validation failed/i);
    await expect(render({ kind: "roadmap", input: { ...roadmapInput, hero: { title: "" } }, context: context("roadmap", "preview") })).rejects.toThrow(/validation failed/i);
  });
});
