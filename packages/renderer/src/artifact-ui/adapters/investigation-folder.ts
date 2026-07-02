/**
 * Investigation-Folder adapter (Issue 004 + Issue 017).
 *
 * Maps InverseThinkingRenderInput → InvestigationFolderTemplateData.
 * Issue 017: frame mapping — 'detective_case' → frameVariant 'detective',
 * anything else → 'neutral'. The single inverse-thinking.html template
 * branches on it.frameVariant.
 *
 * Projection safety (ADR-022): teacher_only blocks included only when
 * audience === 'teacher'. Student HTML never contains teacher DOM.
 */

import type { InverseThinkingRenderInput } from "../../inverse-thinking-renderer.js";

export type InvestigationFolderAudience = "teacher" | "student";
export type InvestigationFolderFrameVariant = "detective" | "neutral";

export interface InvestigationFolderCaseData {
  id: string;
  title: string;
  alias?: string | null;
  disaster: string;
  key_clues: readonly string[];
  safe_zone: string;
  filing_note: string;
  student_task: string;
  teacher_only?: { rationale: string; answer_key: string };
}

export interface InvestigationFolderSummaryRow {
  case_id: string;
  trap: string;
  clue: string;
  safe_rule: string;
}

export interface InvestigationFolderTemplateData {
  artifactCss: string;
  lang: string;
  title: string;
  subtitle?: string;
  frame: "detective_case" | "neutral";
  frameVariant: InvestigationFolderFrameVariant;
  subject: string;
  gradeLevel: string;
  artifactKind: string;
  estimatedMinutes?: number;
  isTeacher: boolean;
  cases: InvestigationFolderCaseData[];
  summaryTable: InvestigationFolderSummaryRow[];
  teacherOnly?: { rationale: string; answer_key: string };
}

export function adaptInverseThinking(
  input: InverseThinkingRenderInput,
  audience: InvestigationFolderAudience,
  artifactCss: string,
): InvestigationFolderTemplateData {
  const isTeacher = audience === "teacher";
  const frameVariant: InvestigationFolderFrameVariant =
    input.frame === "detective_case" ? "detective" : "neutral";

  const cases: InvestigationFolderCaseData[] = input.cases.map((c) => ({
    id: c.id,
    title: c.title,
    alias: c.alias,
    disaster: c.disaster,
    key_clues: c.key_clues,
    safe_zone: c.safe_zone,
    filing_note: c.filing_note,
    student_task: c.student_task,
    teacher_only: isTeacher ? c.teacher_only : undefined,
  }));

  const summaryTable: InvestigationFolderSummaryRow[] = input.summaryTable.map((row) => ({
    case_id: row.case_id,
    trap: row.trap,
    clue: row.clue,
    safe_rule: row.safe_rule,
  }));

  return {
    artifactCss,
    lang: input.lang ?? "vi",
    title: input.title,
    subtitle: `${input.subject} · ${input.gradeLevel}`,
    frame: input.frame,
    frameVariant,
    subject: input.subject,
    gradeLevel: input.gradeLevel,
    artifactKind: input.artifactType,
    isTeacher,
    cases,
    summaryTable,
    teacherOnly: isTeacher ? input.teacherOnly : undefined,
  };
}
