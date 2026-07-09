import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { PracticeSet, SemanticAnchorCluster } from "@oh-my-class/schemas";

import { renderAgentArtifact } from "../src/agent-renderer.js";
import { renderArtifactUi, renderArtifactUiSet } from "../src/artifact-ui/renderer.js";
import type { AnswerKeyData, LessonData } from "../src/contracts/index.js";
import type { RootCauseSessionData } from "../src/contracts/root-cause-session.js";
import type { VideoRouteData } from "../src/contracts/video-route.js";
import { renderInverseThinkingHtml } from "../src/inverse-thinking-renderer.js";
import { renderSemanticAnchorProjection, renderSemanticAnchorProjectionSet } from "../src/semantic-anchor-projections.js";
import { inverseThinkingFixture } from "./inverse-thinking-fixture.js";
import { ACTIVE_ARTIFACT_TYPES, richAgentArtifact } from "./rich-agent-fixtures.js";

const currentDir = dirname(fileURLToPath(import.meta.url));
const baselineDir = join(currentDir, "baselines", "current-renderer");
const shouldUpdateBaselines = process.env.UPDATE_CURRENT_RENDERER_BASELINES === "1";

type BaselineCase = {
  readonly id: string;
  readonly render: () => Promise<string>;
};

type BaselineMetadata = {
  readonly packageName: string;
  readonly packageVersion: string;
  readonly capturedGitCommit: string;
  readonly updateCommand: string;
  readonly baselineIds: readonly string[];
  readonly sourceFiles: readonly string[];
  readonly note: string;
};

const semanticAnchorCluster: SemanticAnchorCluster = {
  cluster_id: "baseline-cluster-001",
  title: "Travel word boundaries",
  title_confidence: 0.9,
  raw_input_span: "travel / journey / trip",
  terms: ["travel", "journey", "trip"],
  review_status: "passed",
  warnings: [],
  teacher_source_notes: ["Cambridge classroom note."],
  contrast_notes: ["Trip is shorter and purpose-bound."],
  summary_rows: ["Use trip for a specific visit."],
  anchors: [
    {
      word: "journey",
      impression_vi: "Một chặng đường.",
      core_trigger_en: "long movement",
      visual_cue_vi: "Con đường dài.",
      semantic_chain: ["move", "path"],
      example_en: "The journey changed her.",
      contrast_note_vi: "Không dùng cho việc đi ngắn.",
      student_explanation_vi: "Journey nhấn vào quá trình.",
      teacher_script_vi: "Ask students what changed.",
      edge_cases: ["Business journey is uncommon."],
      source_notes: ["Oxford: journey is often long."],
    },
  ],
};

const semanticAnchorPracticeSet: PracticeSet = {
  practice_set_id: "baseline-practice-001",
  cluster_id: semanticAnchorCluster.cluster_id,
  items: [
    {
      item_id: "item-1",
      intent: "boundary_explanation",
      prompt: "Explain why 'business trip' is more natural.",
      answer: "Business trip",
      rationale: "Trip names a specific purpose-bound visit.",
    },
  ],
};

const lessonData: LessonData = {
  title: "Baseline Lesson",
  subject: "English",
  gradeLevel: "Grade 8",
  objectives: ["Understand topic vocabulary"],
  sections: [{ heading: "Introduction", body: "Content here." }],
  lang: "vi",
};

const answerKeyData: AnswerKeyData = {
  title: "Baseline Teacher Answers",
  theme: "default",
  accessibility: { language: "vi" },
  sections: [
    {
      id: "answer-1",
      title: "Quiz",
      summary: "1. B — Business trip is purpose-bound.",
    },
  ],
};

const rootCauseData: RootCauseSessionData = {
  title: "Future Perfect vs Continuous",
  subject: "English",
  gradeLevel: "Grade 10",
  lang: "vi",
  sessionCode: "RC-U1-L1",
  difficulty: "mid",
  estimatedMinutes: 45,
  targetConcept: "Future Perfect",
  anchorTimeline: [
    {
      id: "a1",
      label: "T+0",
      event: "Học sinh gặp câu đầu tiên",
      significance: "Điểm neo ban đầu",
      isKeyAnchor: true,
    },
  ],
  comparisons: [],
  generalizationCheckpoints: [
    {
      id: "g1",
      learnerClaim: "Will have + V3 diễn tả hành động hoàn thành trước mốc tương lai",
      verdict: "confirmed",
      evidence: "Ví dụ thực tế",
    },
  ],
  teacherNotes: "Teacher-only baseline note.",
};

const videoRouteData: VideoRouteData = {
  title: "Airport Listening Route",
  subject: "English",
  gradeLevel: "Grade 9",
  unit: "Unit 2",
  estimatedMinutes: 25,
  videoMetadata: { videoDuration: "3:20" },
  stations: [
    { code: "GA01", title: "Khởi động", description: "Xem 15 giây đầu, đoán chủ đề.", catIndex: 1 },
    { code: "GA02", title: "Nghe lần 1", description: "Nghe toàn bài, ghi ý chính.", catIndex: 2 },
  ],
  lang: "vi",
};

const baselineCases: readonly BaselineCase[] = [
  ...ACTIVE_ARTIFACT_TYPES.map((artifactType) => ({
    id: `agent-${artifactType}`,
    render: () => renderAgentArtifact(richAgentArtifact(artifactType)),
  })),
  {
    id: "artifact-ui-lesson",
    render: () => renderArtifactUi({ family: "paper-dossier", kind: "lesson", audience: "student", data: lessonData }),
  },
  {
    id: "artifact-ui-answer-key",
    render: () => renderArtifactUi({ family: "paper-dossier", kind: "answer-key", audience: "student", data: answerKeyData }),
  },
  {
    id: "artifact-ui-root-cause-session-student",
    render: () => renderArtifactUi({ family: "paper-dossier", kind: "root-cause-session", audience: "student", data: rootCauseData }),
  },
  {
    id: "artifact-ui-root-cause-session-teacher",
    render: () => renderArtifactUi({ family: "paper-dossier", kind: "root-cause-session", audience: "teacher", data: rootCauseData }),
  },
  {
    id: "artifact-ui-video-route",
    render: () => renderArtifactUi({ family: "transit-route", kind: "video-route", audience: "student", data: videoRouteData }),
  },
  {
    id: "artifact-ui-inverse-thinking-student",
    render: () => renderArtifactUi({ family: "investigation-folder", kind: "inverse-thinking", audience: "student", data: inverseThinkingFixture }),
  },
  {
    id: "inverse-thinking-wrapper-teacher",
    render: () => renderInverseThinkingHtml({ ...inverseThinkingFixture, artifactType: "teacher_only" }),
  },
  {
    id: "semantic-anchor-wrapper-teaching-teacher",
    render: () => renderSemanticAnchorProjection({ cluster: semanticAnchorCluster, audience: "teacher", kind: "teaching" }),
  },
  {
    id: "semantic-anchor-wrapper-practice-student",
    render: () => renderSemanticAnchorProjection({ cluster: semanticAnchorCluster, practiceSet: semanticAnchorPracticeSet, audience: "student", kind: "practice" }),
  },
  {
    id: "semantic-anchor-wrapper-set",
    render: async () => {
      const set = await renderSemanticAnchorProjectionSet(semanticAnchorCluster, semanticAnchorPracticeSet);
      return [set.teachingTeacherHtml, set.teachingStudentHtml, set.practiceTeacherHtml, set.practiceStudentHtml].join("\n<!-- baseline-split -->\n");
    },
  },
  {
    id: "artifact-ui-vocabulary-set",
    render: async () => {
      const set = await renderArtifactUiSet({ cluster: semanticAnchorCluster, practiceSet: semanticAnchorPracticeSet });
      return [set.teachingTeacher, set.teachingStudent, set.practiceTeacher, set.practiceStudent].join("\n<!-- baseline-split -->\n");
    },
  },
];

function baselinePath(id: string): string {
  return join(baselineDir, `${id}.html`);
}

function currentGitCommit(): string {
  return execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
}

function metadata(): BaselineMetadata {
  const packageJson = JSON.parse(readFileSync(join(currentDir, "..", "package.json"), "utf8"));
  return {
    packageName: String(packageJson.name),
    packageVersion: String(packageJson.version),
    capturedGitCommit: currentGitCommit(),
    updateCommand: "UPDATE_CURRENT_RENDERER_BASELINES=1 pnpm --filter @oh-my-class/renderer exec vitest run __tests__/current-renderer-baselines.test.ts",
    baselineIds: baselineCases.map((baselineCase) => baselineCase.id),
    sourceFiles: [
      "packages/renderer/src/renderer.ts",
      "packages/renderer/src/agent-renderer.ts",
      "packages/renderer/src/artifact-ui/renderer.ts",
      "packages/renderer/src/semantic-anchor-projections.ts",
      "packages/renderer/src/inverse-thinking-renderer.ts",
      "packages/renderer/templates/**",
      "packages/renderer/src/theme/themes/*.json",
    ],
    note: "Phase 0 current-renderer baselines for ADR-025. These snapshots intentionally predate the plugin-registry rewrite.",
  };
}

function writeBaseline(id: string, html: string): void {
  mkdirSync(baselineDir, { recursive: true });
  writeFileSync(baselinePath(id), html, "utf8");
}

describe("current renderer golden baselines", () => {
  it("captures or matches deterministic HTML for every current renderer surface", async () => {
    const rendered = await Promise.all(
      baselineCases.map(async (baselineCase) => ({
        id: baselineCase.id,
        html: await baselineCase.render(),
      })),
    );

    if (shouldUpdateBaselines) {
      for (const result of rendered) {
        writeBaseline(result.id, result.html);
      }
      writeFileSync(join(baselineDir, "metadata.json"), `${JSON.stringify(metadata(), null, 2)}\n`, "utf8");
    }

    for (const result of rendered) {
      expect(result.html).toMatch(/^<!DOCTYPE html>/);
      expect(result.html).not.toMatch(/https?:\/\//);
      expect(result.html).toBe(readFileSync(baselinePath(result.id), "utf8"));
    }
  });
});
