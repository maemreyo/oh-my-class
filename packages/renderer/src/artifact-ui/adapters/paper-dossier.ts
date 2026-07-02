/**
 * Paper-Dossier adapter.
 *
 * Three input shapes map to three template kinds:
 *   LessonData           → lesson.html
 *   AnswerKeyData        → answer-key.html   (with interactivityJS)
 *   RootCauseSessionData → root-cause-session.html (with interactivityJS)
 *
 * The `audience` field drives teacher-only gating for root-cause-session.
 */

import type { LessonData } from "../../contracts/lesson.js";
import type { AnswerKeyData } from "../../contracts/answer_key.js";
import type { ContentComponent, QuestionCardComponent, QuestionListComponent, RoleplayScriptComponent, VocabClusterComponent } from "../../contracts/components.js";
import type {
  RootCauseSessionData,
  GeneralizationCheckpoint,
  ControlledComparison,
  StressTest,
  MetaphorLog,
  MasteryMarker,
  ScenarioAnchor,
  AnchorTimelineEntry,
} from "../../contracts/root-cause-session.js";

export type PaperDossierAudience = "teacher" | "student";

// ── Lesson ───────────────────────────────────────────────────────────────────

function esc(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderLessonComponent(comp: ContentComponent): string {
  switch (comp.type) {
    case "question_card": {
      const opts = Object.entries((comp as QuestionCardComponent).options ?? {});
      const optsHtml = opts.map(([k, v]) => `<div class="option">${esc(k)}. ${esc(v)}</div>`).join("");
      const explainHtml = (comp as QuestionCardComponent).explain
        ? `<div class="question-explanation"><b>Giải thích:</b> ${esc((comp as QuestionCardComponent).explain!)}</div>`
        : "";
      return `<div class="component-question-mc"><p class="question-prompt">${esc((comp as QuestionCardComponent).text)}</p><div class="options-grid">${optsHtml}</div>${explainHtml}</div>`;
    }
    case "question_list":
      return (comp as QuestionListComponent).questions.map(q => renderLessonComponent(q)).join("\n");
    case "roleplay_script": {
      const lines = ((comp as RoleplayScriptComponent).lines ?? [])
        .map(l => `<div class="line roleplay-line"><span class="who ${esc(l.speaker_class ?? l.speaker)}">${esc(l.speaker)}</span><span class="what">${esc(l.text)}</span></div>`)
        .join("");
      return `<div class="script roleplay-card">${lines}</div>`;
    }
    case "vocab_cluster": {
      const c = comp as VocabClusterComponent;
      const items = (c.items ?? [])
        .map(item => `<div class="vocab-cluster__node"><b>${esc(item.word)}</b><span>${esc(item.definition)}</span>${item.example ? `<em>${esc(item.example)}</em>` : ""}</div>`)
        .join("");
      return `<div class="vocab-cluster"><div class="vocab-cluster__header"><b>${esc(c.title)}</b>${c.description ? `<p>${esc(c.description)}</p>` : ""}</div><div class="vocab-cluster__map">${items}</div></div>`;
    }
    case "callout": {
      const titleHtml = comp.title ? `<div class="art-callout-title"><b>${esc(comp.title)}</b></div>` : "";
      return `<div class="art-callout">${titleHtml}<span>${esc(comp.body)}</span></div>`;
    }
    case "flow_step": {
      const steps = (comp.steps ?? []).map(s =>
        `<div class="art-flow-step"><span class="art-mono">${esc(s.time)}</span> <b>${esc(s.title)}</b> — ${esc(s.body)}</div>`
      ).join("");
      return `<div class="art-flow">${steps}</div>`;
    }
    case "heading":
      return `<h${comp.level} class="art-section-heading">${esc(comp.text)}</h${comp.level}>`;
    case "paragraph":
      return `<p>${esc(comp.text)}</p>`;
    default:
      return "";
  }
}

export interface PaperDossierLessonSection {
  heading: string;
  body: string;
  componentsHtml: string;
}

export interface PaperDossierLessonTemplateData {
  artifactCss: string;
  lang: string;
  title: string;
  lede?: string;
  sidebar?: {
    title: string;
    subtitle?: string;
    stat?: { key: string; value: string };
    nav: Array<{ href: string; num?: string; label: string; active?: boolean }>;
    callout?: string;
  };
  objectives: string[];
  phases: Array<{ when: string; heading: string; goal: string; output: string; colorVar: string }>;
  conceptBoxes: Array<{ title: string; link?: string; triad?: Array<{ heading: string; value: string }> }>;
  scripts: Array<{
    heading?: string;
    lines: Array<{ who: string; whoClass?: string; text: string }>;
    key?: string;
  }>;
  homeworkItems: Array<{ tag: string; text: string }>;
  sections: PaperDossierLessonSection[];
}

const catVars = ["var(--art-cat-1)", "var(--art-cat-2)", "var(--art-cat-3)", "var(--art-cat-4)", "var(--art-cat-5)"];

export function adaptLesson(
  data: LessonData,
  artifactCss: string,
): PaperDossierLessonTemplateData {
  const sidebar = data.sidebar
    ? {
        title: data.sidebar.title,
        subtitle: data.sidebar.subtitle,
        stat: data.sidebar.stats?.[0]
          ? { key: data.sidebar.stats[0].key, value: data.sidebar.stats[0].value }
          : undefined,
        nav: (data.sidebar.nav ?? []).map((n) => ({ href: n.href, num: n.num, label: n.label })),
        callout: data.sidebar.linkback,
      }
    : undefined;

  return {
    artifactCss,
    lang: data.lang ?? "vi",
    title: data.title,
    lede: data.hero?.lede,
    sidebar,
    objectives: data.objectives,
    phases: [],
    conceptBoxes: [],
    scripts: [],
    homeworkItems: [],
    sections: (data.sections ?? []).map((sec) => ({
      heading: sec.heading,
      body: sec.body,
      componentsHtml: (sec.components ?? []).map(renderLessonComponent).join("\n"),
    })),
  };
}

// ── Answer Key ────────────────────────────────────────────────────────────────

export interface AnswerKeyQuestion {
  n: number;
  cat: string;
  text: string;
  options: string[];
  correctIndex: number;
  essence: string;
  trap: string;
  wrong: Array<{ letter: string; opt: string; why: string }>;
}

export interface PaperDossierAnswerKeyTemplateData {
  artifactCss: string;
  interactivityJS: string;
  lang: string;
  title: string;
  examTitle?: string;
  groupLegend: Array<{ cat: string; label: string; range: string }>;
  questions: AnswerKeyQuestion[];
}

const catNames = ["cat1", "cat2", "cat3", "cat4", "cat5", "cat6", "cat7"];

export function adaptAnswerKey(
  data: AnswerKeyData,
  artifactCss: string,
  interactivityJS: string,
): PaperDossierAnswerKeyTemplateData {
  const sections = data.sections ?? [];
  const questions: AnswerKeyQuestion[] = [];
  let qNum = 0;
  let sectionStart = 1;
  const groupLegend: PaperDossierAnswerKeyTemplateData["groupLegend"] = [];

  for (let si = 0; si < sections.length; si++) {
    const sec = sections[si];
    const cat = catNames[si % catNames.length];
    // Collect individual question_card + those inside question_list wrappers
    const rawCards: QuestionCardComponent[] = (sec.components ?? []).flatMap((c) => {
      if (c.type === "question_card") return [c as QuestionCardComponent];
      if (c.type === "question_list") return (c as QuestionListComponent).questions;
      return [];
    });

    for (const q of rawCards) {
      qNum++;
      const optionEntries = Object.entries(q.options ?? {});
      const correctLetter = q.answer ?? "";
      const correctIndex = optionEntries.findIndex(([k]) => k === correctLetter);
      const wrongReasons = q.wrong_reasons ?? {};

      questions.push({
        n: qNum,
        cat,
        text: q.text,
        options: optionEntries.map(([k, v]) => `${k}. ${v}`),
        correctIndex: correctIndex >= 0 ? correctIndex : 0,
        essence: q.essence ?? q.explain ?? "",
        trap: q.tip ?? "",
        wrong: optionEntries
          .filter(([k]) => k !== correctLetter)
          .map(([k, v]) => ({
            letter: k,
            opt: v,
            why: wrongReasons[k] ?? "",
          })),
      });
    }

    const sectionEnd = qNum;
    groupLegend.push({
      cat,
      label: sec.title ?? `Phần ${si + 1}`,
      range: sectionStart === sectionEnd
        ? `Câu ${sectionStart}`
        : `Câu ${sectionStart}–${sectionEnd}`,
    });
    sectionStart = qNum + 1;
  }

  return {
    artifactCss,
    interactivityJS,
    lang: data.accessibility?.language ?? "vi",
    title: data.title ?? "Answer Key",
    groupLegend,
    questions,
  };
}

// ── Root-Cause Session ────────────────────────────────────────────────────────

export interface PaperDossierRootCauseTemplateData {
  artifactCss: string;
  interactivityJS: string;
  lang: string;
  title: string;
  lede?: string;
  sessionCode: string;
  difficulty: string;
  estimatedMinutes: number;
  targetConcept: string;
  scenarioAnchors: Array<{ scenario: string; connection: string }>;
  anchorTimelines: Array<{
    heading: string;
    sub?: string;
    entries: Array<{ label: string; event: string; significance: string; isKeyAnchor?: boolean }>;
  }>;
  comparisons: Array<{
    constant: string;
    variants: Array<{ label: string; value: string; isControl?: boolean }>;
    insight: string;
  }>;
  generalizationCheckpoints: Array<{
    learnerClaim: string;
    verdict: "confirmed" | "refined" | "rejected";
    evidence: string;
    refinedClaim?: string;
  }>;
  stressTests: Array<{ brokenExample: string; whyItBreaks: string; fix?: string }>;
  metaphorLogs: Array<{ landedAttempt: string; collapsedAttempts?: string[] }>;
  masteryMarkers: Array<{ label: string; level: "aware" | "applying" | "mastered" }>;
  teacherNotes?: string;
  closingPrompt?: string;
}

export function adaptRootCauseSession(
  data: RootCauseSessionData,
  audience: PaperDossierAudience,
  artifactCss: string,
  interactivityJS: string,
): PaperDossierRootCauseTemplateData {
  const anchorTimelines = (data.anchorTimeline ?? []).length > 0
    ? [{ heading: "Trục thời gian neo", entries: data.anchorTimeline }]
    : [];

  return {
    artifactCss,
    interactivityJS,
    lang: data.lang ?? "vi",
    title: data.title,
    lede: data.subtitle,
    sessionCode: data.sessionCode,
    difficulty: data.difficulty,
    estimatedMinutes: data.estimatedMinutes,
    targetConcept: data.targetConcept,
    scenarioAnchors: (data.scenarioAnchors ?? []).map((s) => ({
      scenario: s.scenario,
      connection: s.connection,
    })),
    anchorTimelines: anchorTimelines.map((tl) => ({
      heading: tl.heading,
      entries: (tl.entries as AnchorTimelineEntry[]).map((e) => ({
        label: e.label,
        event: e.event,
        significance: e.significance,
        isKeyAnchor: e.isKeyAnchor,
      })),
    })),
    comparisons: (data.comparisons ?? []).map((c) => ({
      constant: c.constant,
      variants: c.variants.map((v) => ({ label: v.label, value: v.value, isControl: v.isControl })),
      insight: c.insight,
    })),
    generalizationCheckpoints: (data.generalizationCheckpoints ?? []).map((g) => ({
      learnerClaim: g.learnerClaim,
      verdict: g.verdict,
      evidence: g.evidence,
      refinedClaim: g.refinedClaim,
    })),
    stressTests: (data.stressTests ?? []).map((s) => ({
      brokenExample: s.brokenExample,
      whyItBreaks: s.whyItBreaks,
      fix: s.fix,
    })),
    metaphorLogs: (data.metaphorLogs ?? []).map((m) => ({
      landedAttempt: m.landedAttempt,
      collapsedAttempts: m.collapsedAttempts,
    })),
    masteryMarkers: (data.masteryMarkers ?? []).map((m) => ({
      label: m.label,
      level: m.level,
    })),
    teacherNotes: audience === "teacher" ? data.teacherNotes : undefined,
    closingPrompt: undefined,
  };
}
