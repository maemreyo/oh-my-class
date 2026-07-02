/**
 * Issue 008 — TDD test suite for renderArtifactUi()
 *
 * Tests cover:
 *  - All 4 families render valid standalone HTML
 *  - Audience projection safety (teacher-only content gating)
 *  - Interactivity.js inlining rules
 *  - Sanitizer behavior (no external assets)
 *  - renderArtifactUiSet() batch convenience
 *  - Error paths (unknown family, missing template)
 */

import { describe, expect, it } from "vitest";
import { renderArtifactUi, renderArtifactUiSet } from "../../src/artifact-ui/renderer.js";
import { inverseThinkingFixture } from "../inverse-thinking-fixture.js";
import type { SemanticAnchorCluster, PracticeSet } from "@oh-my-class/schemas";
import type { LessonData } from "../../src/contracts/lesson.js";
import type { VideoRouteData } from "../../src/contracts/video-route.js";
import type { RootCauseSessionData } from "../../src/contracts/root-cause-session.js";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const cluster: SemanticAnchorCluster = {
  cluster_id: "test-cluster-001",
  title: "Travel word boundaries",
  title_confidence: 0.9,
  raw_input_span: "travel / journey / trip",
  terms: ["travel", "journey", "trip"],
  review_status: "passed",
  warnings: [],
  teacher_source_notes: ["Cambridge notes."],
  contrast_notes: ["Trip is shorter than journey."],
  summary_rows: ["Use trip for a specific visit."],
  anchors: [{
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
  }],
};

const practiceSet: PracticeSet = {
  practice_set_id: "test-practice-001",
  cluster_id: "test-cluster-001",
  items: [{
    item_id: "item-1",
    intent: "boundary_explanation",
    prompt: "Explain why 'business trip' is more natural.",
    answer: "Business trip",
    rationale: "Trip names a specific purpose-bound visit.",
  }],
};

const lessonData: LessonData = {
  title: "Test Lesson",
  subject: "English",
  gradeLevel: "Grade 8",
  objectives: ["Understand topic vocabulary"],
  sections: [{ heading: "Introduction", body: "Content here." }],
  lang: "vi",
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

const rootCauseData: RootCauseSessionData = {
  title: "Future Perfect vs Continuous",
  subject: "English",
  gradeLevel: "Grade 10",
  lang: "vi",
  sessionCode: "RC-U1-L1",
  difficulty: "mid",
  estimatedMinutes: 45,
  targetConcept: "Future Perfect",
  anchorTimeline: [{
    id: "a1",
    label: "T+0",
    event: "Học sinh gặp câu đầu tiên",
    significance: "Điểm neo ban đầu",
    isKeyAnchor: true,
  }],
  comparisons: [],
  generalizationCheckpoints: [{
    id: "g1",
    learnerClaim: "Will have + V3 diễn tả hành động hoàn thành trước mốc tương lai",
    verdict: "confirmed",
    evidence: "Ví dụ thực tế",
  }],
};

// ── Navy-Ticket tests ─────────────────────────────────────────────────────────

describe("renderArtifactUi — navy-ticket", () => {
  it("renders teaching teacher as valid standalone HTML", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket",
      kind: "teaching",
      audience: "teacher",
      cluster,
    });
    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain('data-artifact-theme="navy-ticket"');
    expect(html).toContain("oh-my-class");
    expect(html).toContain("<meta name=\"viewport\"");
    expect(html).not.toMatch(/https?:\/\//);
    expect(html).not.toContain("<link");
  });

  it("teaching teacher contains art-projection-flag and teacher block", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket", kind: "teaching", audience: "teacher", cluster,
    });
    expect(html).toContain('class="art-projection-flag"');
    expect(html).toContain('class="art-teacher-block"');
    expect(html).toContain("Kịch bản giảng");
    expect(html).toContain("Ask students what changed");
  });

  it("teaching student has NO teacher-only content", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket", kind: "teaching", audience: "student", cluster,
    });
    expect(html).not.toContain('class="art-projection-flag"');
    expect(html).not.toContain('class="art-teacher-block"');
    expect(html).not.toContain("Ask students what changed");
    expect(html).not.toContain("Oxford: journey is often long");
    expect(html).toContain("journey");
    expect(html).toContain("Journey nhấn vào quá trình");
  });

  it("practice teacher contains answer and rationale", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket", kind: "practice", audience: "teacher", cluster, practiceSet,
    });
    expect(html).toContain("Business trip");
    expect(html).toContain("purpose-bound visit");
    expect(html).toContain('class="art-projection-flag"');
  });

  it("practice student has NO answer or rationale", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket", kind: "practice", audience: "student", cluster, practiceSet,
    });
    expect(html).not.toContain("Business trip");
    expect(html).not.toContain("purpose-bound visit");
    expect(html).not.toContain('class="art-projection-flag"');
    expect(html).toContain("Explain why");
  });

  it("output contains no <script> block (no interactivity needed)", async () => {
    const html = await renderArtifactUi({
      family: "navy-ticket", kind: "teaching", audience: "student", cluster,
    });
    expect(html).not.toContain("<script");
  });
});

// ── Paper-Dossier tests ────────────────────────────────────────────────────────

describe("renderArtifactUi — paper-dossier lesson", () => {
  it("renders lesson as valid standalone HTML with paper-dossier theme", async () => {
    const html = await renderArtifactUi({
      family: "paper-dossier", kind: "lesson", audience: "student", data: lessonData,
    });
    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain('data-artifact-theme="paper-dossier"');
    expect(html).toContain("oh-my-class");
    expect(html).toContain("Test Lesson");
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("lesson output contains NO teacher-only elements", async () => {
    const html = await renderArtifactUi({
      family: "paper-dossier", kind: "lesson", audience: "student", data: lessonData,
    });
    expect(html).not.toContain('class="art-teacher-block"');
    expect(html).not.toContain('class="art-projection-flag"');
  });

  it("lesson output does NOT contain interactivity script", async () => {
    const html = await renderArtifactUi({
      family: "paper-dossier", kind: "lesson", audience: "student", data: lessonData,
    });
    expect(html).not.toContain("data-toggle-reveal");
  });
});

describe("renderArtifactUi — paper-dossier root-cause-session", () => {
  it("renders root-cause-session with paper-dossier theme", async () => {
    const html = await renderArtifactUi({
      family: "paper-dossier", kind: "root-cause-session", audience: "student", data: rootCauseData,
    });
    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain('data-artifact-theme="paper-dossier"');
    expect(html).toContain("Future Perfect");
  });

  it("root-cause-session contains interactivity script in <head>", async () => {
    const html = await renderArtifactUi({
      family: "paper-dossier", kind: "root-cause-session", audience: "student", data: rootCauseData,
    });
    // Script must be in <head> — body sanitizer never touches it
    const headSection = html.slice(html.indexOf("<head>"), html.indexOf("</head>"));
    expect(headSection).toContain("<script>");
    expect(headSection).not.toContain("eval(");
  });

  it("root-cause-session teacher sees teacher notes", async () => {
    const withNotes: RootCauseSessionData = { ...rootCauseData, teacherNotes: "Chú ý khi học sinh tự đề xuất" };
    const teacherHtml = await renderArtifactUi({
      family: "paper-dossier", kind: "root-cause-session", audience: "teacher", data: withNotes,
    });
    expect(teacherHtml).toContain("Chú ý khi học sinh tự đề xuất");

    const studentHtml = await renderArtifactUi({
      family: "paper-dossier", kind: "root-cause-session", audience: "student", data: withNotes,
    });
    expect(studentHtml).not.toContain("Chú ý khi học sinh tự đề xuất");
  });
});

// ── Transit-Route tests ────────────────────────────────────────────────────────

describe("renderArtifactUi — transit-route", () => {
  it("renders video-route with transit-route theme", async () => {
    const html = await renderArtifactUi({
      family: "transit-route", kind: "video-route", audience: "student", data: videoRouteData,
    });
    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain('data-artifact-theme="transit-route"');
    expect(html).toContain("oh-my-class");
    expect(html).toContain("GA01");
    expect(html).toContain("GA02");
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("output contains art-ticket-header and art-station", async () => {
    const html = await renderArtifactUi({
      family: "transit-route", kind: "video-route", audience: "student", data: videoRouteData,
    });
    expect(html).toContain("art-ticket-header");
    expect(html).toContain("art-station");
  });

  it("output contains NO <video> or <iframe> tags (INVARIANT-04)", async () => {
    const html = await renderArtifactUi({
      family: "transit-route", kind: "video-route", audience: "student", data: videoRouteData,
    });
    expect(html).not.toContain("<video");
    expect(html).not.toContain("<iframe");
  });

  it("output contains no <script> block", async () => {
    const html = await renderArtifactUi({
      family: "transit-route", kind: "video-route", audience: "student", data: videoRouteData,
    });
    expect(html).not.toContain("<script");
  });
});

// ── Investigation-Folder tests ─────────────────────────────────────────────────

describe("renderArtifactUi — investigation-folder", () => {
  it("renders inverse-thinking with investigation-folder theme", async () => {
    const html = await renderArtifactUi({
      family: "investigation-folder",
      kind: "inverse-thinking",
      audience: "student",
      data: inverseThinkingFixture,
    });
    expect(html).toMatch(/^<!DOCTYPE html>/);
    expect(html).toContain('data-artifact-theme="investigation-folder"');
    expect(html).toContain("oh-my-class");
    expect(html).not.toMatch(/https?:\/\//);
  });

  it("detective frame → art-cover--folder--detective", async () => {
    const html = await renderArtifactUi({
      family: "investigation-folder",
      kind: "inverse-thinking",
      audience: "student",
      data: { ...inverseThinkingFixture, frame: "detective_case" },
    });
    expect(html).toContain("art-cover--folder--detective");
    expect(html).not.toContain("art-cover--folder--neutral");
  });

  it("neutral frame → art-cover--folder--neutral", async () => {
    const html = await renderArtifactUi({
      family: "investigation-folder",
      kind: "inverse-thinking",
      audience: "student",
      data: { ...inverseThinkingFixture, frame: "neutral" },
    });
    expect(html).toContain("art-cover--folder--neutral");
    expect(html).not.toContain("art-cover--folder--detective");
  });

  it("teacher_only audience → art-projection-flag present", async () => {
    const html = await renderArtifactUi({
      family: "investigation-folder",
      kind: "inverse-thinking",
      audience: "teacher",
      data: inverseThinkingFixture,
    });
    expect(html).toContain('class="art-projection-flag"');
  });

  it("student audience → NO art-teacher-block or art-projection-flag", async () => {
    const html = await renderArtifactUi({
      family: "investigation-folder",
      kind: "inverse-thinking",
      audience: "student",
      data: inverseThinkingFixture,
    });
    expect(html).not.toContain('class="art-projection-flag"');
    expect(html).not.toContain('class="art-teacher-block"');
  });
});

// ── Error paths ────────────────────────────────────────────────────────────────

describe("renderArtifactUi — error handling", () => {
  it("throws descriptive error for unknown family", async () => {
    await expect(
      renderArtifactUi({ family: "unknown-family" as never, kind: "lesson" as never, audience: "student", data: {} as never }),
    ).rejects.toThrow(/Unknown Artifact UI family/);
  });
});

// ── renderArtifactUiSet ───────────────────────────────────────────────────────

describe("renderArtifactUiSet", () => {
  it("returns all 4 projections", async () => {
    const set = await renderArtifactUiSet({ cluster, practiceSet });
    expect(set.teachingTeacher).toContain('data-artifact-theme="navy-ticket"');
    expect(set.teachingStudent).toContain('data-artifact-theme="navy-ticket"');
    expect(set.practiceTeacher).toContain('data-artifact-theme="navy-ticket"');
    expect(set.practiceStudent).toContain('data-artifact-theme="navy-ticket"');
  });

  it("teachingTeacher has art-projection-flag, teachingStudent does not", async () => {
    const set = await renderArtifactUiSet({ cluster, practiceSet });
    expect(set.teachingTeacher).toContain('class="art-projection-flag"');
    expect(set.teachingStudent).not.toContain('class="art-projection-flag"');
  });

  it("all projections are standalone HTML (no external URLs)", async () => {
    const set = await renderArtifactUiSet({ cluster, practiceSet });
    for (const html of Object.values(set)) {
      expect(html).toMatch(/^<!DOCTYPE html>/);
      expect(html).not.toMatch(/https?:\/\//);
      expect(html).not.toContain("<link");
    }
  });

  it("none of the projections contain eval()", async () => {
    const set = await renderArtifactUiSet({ cluster, practiceSet });
    for (const html of Object.values(set)) {
      expect(html).not.toContain("eval(");
    }
  });
});
