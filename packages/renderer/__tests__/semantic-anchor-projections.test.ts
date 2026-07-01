import { describe, expect, it } from "vitest";

import { renderSemanticAnchorProjectionSet } from "../src/semantic-anchor-projections.js";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

const cluster: SemanticAnchorCluster = {
  cluster_id: "cluster-travel",
  title: "Travel word boundaries",
  title_confidence: 0.82,
  raw_input_span: "travel / journey / trip / voyage",
  terms: ["travel", "journey", "trip", "voyage"],
  review_status: "needs_review",
  warnings: ["Thin evidence for voyage vs journey."],
  teacher_source_notes: ["Cambridge notes journey emphasizes distance and experience."],
  contrast_notes: ["Trip is shorter and more concrete than journey."],
  summary_rows: ["Use trip for a specific visit; journey for the process."],
  anchors: [{
    word: "journey",
    impression_vi: "Một chặng đường có trải nghiệm.",
    core_trigger_en: "long meaningful movement",
    visual_cue_vi: "Con đường dài có nhiều mốc.",
    semantic_chain: ["move", "path", "experience"],
    example_en: "The journey across the mountains changed her.",
    contrast_note_vi: "Không dùng journey cho việc đi siêu thị ngắn.",
    student_explanation_vi: "Journey nhấn vào quá trình đi và điều học được.",
    teacher_script_vi: "Ask students what changed during the movement, not only where they went.",
    edge_cases: ["Business journey is uncommon; business trip is natural."],
    source_notes: ["Oxford learner note: journey is often long."],
  }],
};

const practiceSet: PracticeSet = {
  practice_set_id: "practice-travel",
  cluster_id: "cluster-travel",
  items: [{
    item_id: "item-1",
    intent: "boundary_explanation",
    prompt: "Explain why 'business trip' is more natural than 'business journey'.",
    answer: "Business trip",
    rationale: "Trip names a specific purpose-bound visit; journey overemphasizes the process.",
  }],
};

describe("semantic anchor projections", () => {
  it("keeps teacher annotations out of student teaching and practice HTML", () => {
    const projections = renderSemanticAnchorProjectionSet(cluster, practiceSet);

    expect(projections.teachingTeacherHtml).toContain("Teacher script");
    expect(projections.teachingTeacherHtml).toContain("Ask students what changed");
    expect(projections.teachingTeacherHtml).toContain("Thin evidence");
    expect(projections.teachingTeacherHtml).toContain("Title confidence: 82%");
    expect(projections.teachingStudentHtml).toContain("Journey nhấn vào quá trình");
    expect(projections.teachingStudentHtml).not.toContain("Teacher script");
    expect(projections.teachingStudentHtml).not.toContain("Ask students what changed");
    expect(projections.teachingStudentHtml).not.toContain("Title confidence");
    expect(projections.teachingStudentHtml).not.toContain("Oxford learner note");

    expect(projections.practiceTeacherHtml).toContain("Answer rationale");
    expect(projections.practiceTeacherHtml).toContain("Business trip");
    expect(projections.practiceTeacherHtml).toContain("purpose-bound visit");
    expect(projections.practiceStudentHtml).toContain("Explain why");
    expect(projections.practiceStudentHtml).not.toContain("Answer rationale");
    expect(projections.practiceStudentHtml).not.toContain("purpose-bound visit");
  });

  it("emits standalone offline HTML without external URLs", () => {
    const projections = renderSemanticAnchorProjectionSet(cluster, practiceSet);
    const htmlFiles = Object.values(projections);

    for (const html of htmlFiles) {
      expect(html).toMatch(/^<!DOCTYPE html>/);
      expect(html).toContain("<meta name=\"viewport\"");
      expect(html).toContain("oh-my-class");
      expect(html).not.toMatch(/https?:\/\//);
      expect(html).not.toContain("<link");
      expect(html).not.toContain("<script");
    }
  });
});
