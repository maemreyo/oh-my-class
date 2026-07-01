import { describe, expect, it } from "vitest";
import { strFromU8, unzipSync } from "fflate";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

import { buildVocabularyBatchPackage } from "../src/vocabulary-batch/index.js";

const passedCluster: SemanticAnchorCluster = {
  cluster_id: "cluster-passed",
  title: "Travel words",
  title_confidence: 0.86,
  raw_input_span: "travel / journey / trip",
  terms: ["travel", "journey", "trip"],
  review_status: "passed",
  warnings: [],
  teacher_source_notes: ["teacher-only source note"],
  contrast_notes: ["Trip is a specific visit."],
  summary_rows: ["Journey emphasizes the process."],
  anchors: [{
    word: "journey",
    impression_vi: "Một hành trình có trải nghiệm.",
    core_trigger_en: "meaningful movement",
    visual_cue_vi: "Long road",
    semantic_chain: ["move", "experience"],
    example_en: "The journey changed her.",
    contrast_note_vi: "Không dùng cho việc đi ngắn.",
    student_explanation_vi: "Journey nhấn vào quá trình.",
    teacher_script_vi: "Teacher-only script",
    edge_cases: ["business trip is more natural"],
    source_notes: ["teacher-only anchor source"],
  }],
};

const needsReviewCluster: SemanticAnchorCluster = {
  ...passedCluster,
  cluster_id: "cluster-review",
  title: "Thin evidence words",
  review_status: "needs_review",
  warnings: ["Thin source evidence."],
};

const failedCluster: SemanticAnchorCluster = {
  ...passedCluster,
  cluster_id: "cluster-failed",
  title: "Failed words",
  review_status: "failed",
  warnings: ["Projection leakage detected."],
};

const practiceSet: PracticeSet = {
  practice_set_id: "practice-passed",
  cluster_id: "cluster-passed",
  items: [{
    item_id: "item-1",
    intent: "boundary_explanation",
    prompt: "Explain why business trip is natural.",
    answer: "business trip",
    rationale: "Trip is a specific purpose-bound visit.",
  }],
};

function text(files: Record<string, Uint8Array>, path: string): string {
  const file = files[path];
  if (!file) throw new Error(`Missing zip file ${path}`);
  return strFromU8(file);
}

describe("buildVocabularyBatchPackage", () => {
  it("creates an offline index, manifest, and per-cluster folders", async () => {
    const result = await buildVocabularyBatchPackage({
      batchId: "batch-1",
      title: "Vocabulary Batch",
      formats: ["html"],
      clusters: [{ cluster: passedCluster, practiceSet }],
    });
    const files = unzipSync(result.zip);

    expect(files["index.html"]).toBeDefined();
    expect(files["manifest.json"]).toBeDefined();
    expect(files["clusters/cluster-passed/teaching-teacher.html"]).toBeDefined();
    expect(files["clusters/cluster-passed/teaching-student.html"]).toBeDefined();
    expect(text(files, "index.html")).toContain("Vocabulary Batch");
    expect(text(files, "index.html")).not.toMatch(/https?:\/\//);
    expect(text(files, "index.html")).not.toContain("<script");
  });

  it("applies passed, needs_review, and failed export policies", async () => {
    const result = await buildVocabularyBatchPackage({
      batchId: "batch-2",
      title: "Policy Batch",
      formats: ["html", "gift"],
      clusters: [
        { cluster: passedCluster, practiceSet },
        { cluster: needsReviewCluster, practiceSet },
        { cluster: failedCluster, diagnostics: ["Student HTML leaked rationale."] },
      ],
    });
    const files = unzipSync(result.zip);

    expect(files["clusters/cluster-passed/teaching-student.html"]).toBeDefined();
    expect(files["clusters/cluster-passed/practice.gift.txt"]).toBeDefined();
    expect(files["clusters/cluster-review/teaching-teacher.html"]).toBeDefined();
    expect(files["clusters/cluster-review/practice-teacher.html"]).toBeDefined();
    expect(files["clusters/cluster-review/teaching-student.html"]).toBeUndefined();
    expect(files["clusters/cluster-review/practice.gift.txt"]).toBeUndefined();
    expect(files["clusters/cluster-failed/diagnostics.html"]).toBeDefined();
    expect(files["clusters/cluster-failed/teaching-teacher.html"]).toBeUndefined();

    expect(result.manifest.clusters.map((cluster) => cluster.exportStatus)).toEqual([
      "passed",
      "needs_review",
      "failed",
    ]);
  });

  it("generates LMS exports only from student-safe practice data", async () => {
    const result = await buildVocabularyBatchPackage({
      batchId: "batch-3",
      title: "LMS Batch",
      formats: ["gift", "h5p"],
      clusters: [{ cluster: passedCluster, practiceSet }],
    });
    const files = unzipSync(result.zip);
    const gift = text(files, "clusters/cluster-passed/practice.gift.txt");
    const h5p = unzipSync(files["clusters/cluster-passed/practice.h5p"] ?? new Uint8Array());
    const content = text(h5p, "content/content.json");

    expect(gift).toContain("Explain why business trip is natural.");
    expect(gift).toContain("=business trip");
    expect(gift).not.toContain("Teacher-only script");
    expect(gift).not.toContain("teacher-only source note");
    expect(content).toContain("Explain why business trip is natural.");
    expect(content).toContain("business trip");
    expect(content).not.toContain("Teacher-only script");
    expect(content).not.toContain("purpose-bound visit");
  });

  it("links only files that exist in manifest and index", async () => {
    const result = await buildVocabularyBatchPackage({
      batchId: "batch-4",
      title: "Index Batch",
      formats: ["html"],
      clusters: [{ cluster: needsReviewCluster, practiceSet }],
    });
    const files = unzipSync(result.zip);
    const index = text(files, "index.html");
    const manifest = JSON.parse(text(files, "manifest.json")) as typeof result.manifest;

    for (const cluster of manifest.clusters) {
      for (const file of cluster.files) {
        expect(files[file.path]).toBeDefined();
        expect(index).toContain(file.path);
      }
    }
    expect(index).toContain("Thin source evidence.");
    expect(index).toContain("needs_review");
    expect(index).not.toContain("teaching-student.html");
  });
});
