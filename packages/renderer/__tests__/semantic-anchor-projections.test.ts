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

describe("semantic anchor projections (Artifact UI — navy-ticket)", () => {
  it("keeps teacher annotations out of student projections", async () => {
    const projections = await renderSemanticAnchorProjectionSet(cluster, practiceSet);

    // Teacher projection: projection flag + teacher block present
    expect(projections.teachingTeacherHtml).toContain('class="art-projection-flag"');
    expect(projections.teachingTeacherHtml).toContain('class="art-teacher-block"');
    expect(projections.teachingTeacherHtml).toContain("Ask students what changed");

    // Student projection: no teacher-only content
    expect(projections.teachingStudentHtml).toContain("Journey nhấn vào quá trình");
    expect(projections.teachingStudentHtml).not.toContain('class="art-projection-flag"');
    expect(projections.teachingStudentHtml).not.toContain('class="art-teacher-block"');
    expect(projections.teachingStudentHtml).not.toContain("Ask students what changed");
    expect(projections.teachingStudentHtml).not.toContain("Oxford learner note");

    // Practice teacher: has answer and rationale
    expect(projections.practiceTeacherHtml).toContain("Business trip");
    expect(projections.practiceTeacherHtml).toContain("purpose-bound visit");

    // Practice student: no answers
    expect(projections.practiceStudentHtml).toContain("Explain why");
    expect(projections.practiceStudentHtml).not.toContain("Business trip");
    expect(projections.practiceStudentHtml).not.toContain("purpose-bound visit");
  });

  it("emits standalone offline HTML without external URLs", async () => {
    const projections = await renderSemanticAnchorProjectionSet(cluster, practiceSet);
    const htmlFiles = Object.values(projections);

    for (const html of htmlFiles) {
      expect(html).toMatch(/^<!DOCTYPE html>/);
      expect(html).toContain("<meta name=\"viewport\"");
      expect(html).toContain("oh-my-class");
      expect(html).not.toMatch(/https?:\/\//);
      expect(html).not.toContain("<link");
    }
  });

  it("all projections use data-artifact-theme=navy-ticket", async () => {
    const projections = await renderSemanticAnchorProjectionSet(cluster, practiceSet);
    for (const html of Object.values(projections)) {
      expect(html).toContain('data-artifact-theme="navy-ticket"');
    }
  });
});
