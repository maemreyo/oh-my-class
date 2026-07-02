import { describe, expect, it } from "vitest";

import { RendererErrorCode, render, renderBatch, rendererPluginMetadata } from "../src/renderer.js";
import type { RenderContext } from "../src/renderer.js";
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

function context(audience: RenderContext["audience"], renderMode: RenderContext["renderMode"]): RenderContext {
  return {
    audience,
    locale: "vi",
    theme: "default",
    renderMode,
    requestId: `navy-ticket-${audience}-${renderMode}`,
    versions: { rendererVersion: "test-renderer" },
    assetPolicy: "inline-only",
  };
}

describe("navy-ticket vocabulary plugins", () => {
  it("declares registry metadata for teaching and practice projections", () => {
    const metadata = rendererPluginMetadata();

    expect(metadata).toContainEqual({ kind: "navy-ticket.teaching", version: "0.1.0", templateVersion: "navy-ticket-teaching-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "navy-ticket-policy-v1" });
    expect(metadata).toContainEqual({ kind: "navy-ticket.practice", version: "0.1.0", templateVersion: "navy-ticket-practice-template-v1", themeVersion: "theme-resolver-v1", supportedAudiences: ["teacher", "student"], supportsPrint: true, sanitizerPolicyVersion: "navy-ticket-policy-v1" });
  });

  it("renders teacher and student teaching projections without leaking teacher notes to students", async () => {
    const teacher = await render({ kind: "navy-ticket.teaching", input: { cluster }, context: context("teacher", "preview") });
    const student = await render({ kind: "navy-ticket.teaching", input: { cluster }, context: context("student", "preview") });

    expect(teacher.html).toMatch(/^<!DOCTYPE html>/);
    expect(teacher.html).toContain('data-artifact-theme="navy-ticket"');
    expect(teacher.html).toContain("Ask students what changed");
    expect(teacher.manifest.kind).toBe("navy-ticket.teaching");
    expect(student.html).toContain("Journey nhấn vào quá trình");
    expect(student.html).not.toContain("Ask students what changed");
    expect(student.html).not.toContain("Oxford learner note");
    expect(student.html).not.toMatch(/https?:\/\//);
  });

  it("renders practice projections through renderBatch and returns manifests for all variants", async () => {
    const responses = await renderBatch({
      requests: [
        { kind: "navy-ticket.teaching", input: { cluster }, context: context("teacher", "export") },
        { kind: "navy-ticket.teaching", input: { cluster }, context: context("student", "export") },
        { kind: "navy-ticket.practice", input: { cluster, practiceSet }, context: context("teacher", "export") },
        { kind: "navy-ticket.practice", input: { cluster, practiceSet }, context: context("student", "export") },
      ],
    });

    expect(responses.map((response) => response.manifest.kind)).toEqual([
      "navy-ticket.teaching",
      "navy-ticket.teaching",
      "navy-ticket.practice",
      "navy-ticket.practice",
    ]);
    expect(responses[2]?.html).toContain("Business trip");
    expect(responses[2]?.html).toContain("purpose-bound visit");
    expect(responses[3]?.html).toContain("Explain why");
    expect(responses[3]?.html).not.toContain("Business trip");
    expect(responses[3]?.html).not.toContain("purpose-bound visit");
  });

  it("rejects malformed semantic-anchor inputs before rendering", async () => {
    await expect(render({ kind: "navy-ticket.teaching", input: { cluster: { ...cluster, anchors: [] } }, context: context("student", "preview") })).rejects.toMatchObject({ code: RendererErrorCode.ValidationFailed });
    await expect(render({ kind: "navy-ticket.practice", input: { cluster, practiceSet: { ...practiceSet, items: [] } }, context: context("student", "preview") })).rejects.toMatchObject({ code: RendererErrorCode.ValidationFailed });
  });
});
