import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { unzipSync } from "fflate";
import { describe, expect, it } from "vitest";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

import { runVocabularyBatchPackageCli } from "../src/vocabulary-batch/cli.js";

const cluster: SemanticAnchorCluster = {
  cluster_id: "runtime-cluster",
  title: "Runtime vocabulary",
  title_confidence: 0.9,
  raw_input_span: "trip / journey",
  terms: ["trip", "journey"],
  review_status: "passed",
  warnings: [],
  teacher_source_notes: [],
  contrast_notes: ["Trip is specific; journey emphasizes process."],
  summary_rows: ["Trip is often short."],
  anchors: [{
    word: "journey",
    impression_vi: "Hành trình có trải nghiệm.",
    core_trigger_en: "meaningful movement",
    visual_cue_vi: "Con đường dài",
    semantic_chain: ["move", "experience"],
    example_en: "The journey changed her.",
    contrast_note_vi: "Không dùng cho việc đi ngắn.",
    student_explanation_vi: "Journey nhấn vào quá trình.",
    teacher_script_vi: "Teacher script",
    edge_cases: [],
    source_notes: [],
  }],
};

const practiceSet: PracticeSet = {
  practice_set_id: "practice-runtime",
  cluster_id: "runtime-cluster",
  items: [{
    item_id: "item-1",
    intent: "boundary_explanation",
    prompt: "Explain why journey fits.",
    answer: "journey",
    rationale: "Journey emphasizes process.",
  }],
};

describe("vocabulary batch CLI", () => {
  it("writes a zip package for the gateway bridge", async () => {
    const outputDir = await mkdtemp(join(tmpdir(), "omc-vocab-"));
    try {
      const payload = JSON.stringify({
        batchId: "batch-runtime",
        title: "Runtime Batch",
        outputDir,
        formats: ["html"],
        clusters: [{ cluster, practiceSet }],
      });

      const parsed: unknown = JSON.parse(await runVocabularyBatchPackageCli(payload));
      if (!isCliResult(parsed)) throw new Error("Invalid CLI result");
      const files = unzipSync(await readFile(parsed.path));

      expect(files["index.html"]).toBeDefined();
      expect(files["manifest.json"]).toBeDefined();
    } finally {
      await rm(outputDir, { recursive: true, force: true });
    }
  });
});

function isCliResult(value: unknown): value is { readonly path: string } {
  return typeof value === "object" && value !== null && "path" in value && typeof value.path === "string";
}
