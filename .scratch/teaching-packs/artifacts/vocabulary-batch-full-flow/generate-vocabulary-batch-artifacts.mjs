import { mkdir, writeFile } from "node:fs/promises";
import { strFromU8, unzipSync } from "../../../../packages/exporters/node_modules/fflate/esm/browser.js";

import { buildVocabularyBatchPackage } from "../../../../packages/exporters/dist/index.js";

const outputDir = new URL("./", import.meta.url);
const extractedDir = new URL("./extracted/", outputDir);

const passedCluster = {
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

const needsReviewCluster = {
  ...passedCluster,
  cluster_id: "cluster-review",
  title: "Thin evidence words",
  review_status: "needs_review",
  warnings: ["Thin source evidence."],
};

const failedCluster = {
  ...passedCluster,
  cluster_id: "cluster-failed",
  title: "Failed words",
  review_status: "failed",
  warnings: ["Projection leakage detected."],
};

const practiceSet = {
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

const result = await buildVocabularyBatchPackage({
  batchId: "batch-full-flow",
  title: "Vocabulary Batch Full Flow",
  formats: ["html", "gift", "h5p"],
  clusters: [
    { cluster: passedCluster, practiceSet, teacherApproved: true },
    { cluster: needsReviewCluster, practiceSet },
    { cluster: failedCluster, diagnostics: ["Student HTML leaked rationale."] },
  ],
});

await mkdir(extractedDir, { recursive: true });
await writeFile(new URL("./vocabulary-batch-full-flow.zip", outputDir), result.zip);
await writeFile(new URL("./manifest.json", outputDir), JSON.stringify(result.manifest, null, 2));

const files = unzipSync(result.zip);
for (const [path, bytes] of Object.entries(files)) {
  const target = new URL(`./extracted/${path}`, outputDir);
  await mkdir(new URL("./", target), { recursive: true });
  await writeFile(target, bytes);
}

const studentTeaching = strFromU8(files["clusters/cluster-passed/teaching-student.html"]);
const studentPractice = strFromU8(files["clusters/cluster-passed/practice-student.html"]);
const index = strFromU8(files["index.html"]);
const gift = strFromU8(files["clusters/cluster-passed/practice.gift.txt"]);
const h5pFiles = unzipSync(files["clusters/cluster-passed/practice.h5p"]);
const h5pContent = strFromU8(h5pFiles["content/content.json"]);

const leakedTerms = ["Teacher-only script", "teacher-only source note", "teacher-only anchor source", "purpose-bound visit"];
const studentLeakage = leakedTerms.filter((term) => studentTeaching.includes(term) || studentPractice.includes(term));
const lmsLeakage = leakedTerms.filter((term) => gift.includes(term) || h5pContent.includes(term));
const httpAssets = Object.entries(files).filter(([path, bytes]) => {
  if (!path.endsWith(".html")) return false;
  return /https?:\/\//.test(strFromU8(bytes));
});

await writeFile(new URL("./inspection-summary.json", outputDir), JSON.stringify({
  files: Object.keys(files).sort(),
  manifest: result.manifest,
  studentLeakage,
  lmsLeakage,
  httpAssetFiles: httpAssets.map(([path]) => path),
  indexHasScriptTag: index.includes("<script"),
}, null, 2));

if (studentLeakage.length > 0 || lmsLeakage.length > 0 || httpAssets.length > 0 || index.includes("<script")) {
  process.exitCode = 1;
}
