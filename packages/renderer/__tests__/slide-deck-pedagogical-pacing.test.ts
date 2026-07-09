import { describe, expect, it } from "vitest";

import { renderArtifact } from "../src/renderer.js";
import { projectSlideDeckSurface } from "../src/slide-deck-projection.js";
import type { SlideDeckData } from "../src/contracts/index.js";

// ADR-045 (SDTF-02): pedagogical role + planned duration are lesson-planning
// metadata, not student-facing content -- only the teacher (and review)
// surface should ever see a lesson-flow/pacing summary.
const deck: SlideDeckData = {
  deck_id: "deck-pacing-test",
  title: "Pacing Test Deck",
  locale: "en-US",
  theme: "default",
  surfaces: {
    student: { mode: "presentation", export_format: "html" },
    teacher: { mode: "teacher_guide", export_format: "html" },
    print: { mode: "print", export_format: "html" },
  },
  slides: [
    {
      slide_id: "slide-title",
      title: "Fractions",
      layout: "title",
      progression: { step_index: 1, reveal_policy: "all_at_once" },
      blocks: [{ block_id: "block-title", block_type: "heading", body: "Fractions" }],
      pedagogical_role: "hook",
      planned_duration_minutes: 3,
    },
    {
      slide_id: "slide-goal",
      title: "Learning Goal",
      layout: "content",
      progression: { step_index: 2, reveal_policy: "progressive" },
      blocks: [{ block_id: "block-goal", block_type: "paragraph", body: "Explain equivalence." }],
      pedagogical_role: "objective",
      planned_duration_minutes: 4.5,
    },
  ],
  accessibility: { reading_level: "Grade 5", language: "en", alt_text_required: true, keyboard_navigation: true },
  media_policy: { default_tier: "packaged", online_optional_allowed: false, fallback_required: false },
};

describe("slide deck lesson-flow/pacing projection", () => {
  it("exposes lesson flow and total planned minutes only on the teacher surface", () => {
    const teacher = projectSlideDeckSurface({ ...deck, render_surface: "teacher" });
    const student = projectSlideDeckSurface({ ...deck, render_surface: "student" });
    const print = projectSlideDeckSurface({ ...deck, render_surface: "print" });

    expect(teacher.lessonFlow).toEqual([
      { slideId: "slide-title", title: "Fractions", pedagogicalRole: "hook", plannedMinutes: 3 },
      { slideId: "slide-goal", title: "Learning Goal", pedagogicalRole: "objective", plannedMinutes: 4.5 },
    ]);
    expect(teacher.totalPlannedMinutes).toBe(7.5);

    expect(student.lessonFlow).toEqual([]);
    expect(student.totalPlannedMinutes).toBeNull();
    expect(print.lessonFlow).toEqual([]);
    expect(print.totalPlannedMinutes).toBeNull();
  });

  it("labels a slide with no assigned role as unassigned instead of throwing", () => {
    const projected = projectSlideDeckSurface({
      ...deck,
      slides: [{ ...deck.slides[0], pedagogical_role: null, planned_duration_minutes: null }],
      render_surface: "teacher",
    });

    expect(projected.lessonFlow).toEqual([
      { slideId: "slide-title", title: "Fractions", pedagogicalRole: "unassigned", plannedMinutes: null },
    ]);
    expect(projected.totalPlannedMinutes).toBeNull();
  });
});

describe("slide deck lesson-flow/pacing HTML", () => {
  it("renders the lesson-flow summary on the teacher surface", async () => {
    const html = await renderArtifact("slide_deck", { ...deck, render_surface: "teacher" });

    expect(html).toContain("Lesson flow");
    expect(html).toContain("hook");
    expect(html).toContain("objective");
    expect(html).toContain("3 min");
    expect(html).toContain("Total planned time: 7.5 min");
  });

  it("never shows the lesson-flow summary on student or print surfaces", async () => {
    const studentHtml = await renderArtifact("slide_deck", { ...deck, render_surface: "student" });
    const printHtml = await renderArtifact("slide_deck", { ...deck, render_surface: "print" });

    expect(studentHtml).not.toContain("Lesson flow");
    expect(studentHtml).not.toContain("Total planned time");
    expect(printHtml).not.toContain("Lesson flow");
    expect(printHtml).not.toContain("Total planned time");
  });
});
