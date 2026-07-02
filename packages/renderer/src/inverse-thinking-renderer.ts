/**
 * Inverse-thinking renderer — Artifact UI implementation (Issue 006).
 *
 * Delegates to renderArtifactUi() with the investigation-folder family.
 * Old inline CSS (styles()) and string building removed.
 * Public types remain unchanged for backward compatibility.
 *
 * Audience mapping: artifactType === 'teacher_only' → audience:'teacher'
 *                   all other kinds              → audience:'student'
 * Frame mapping (Issue 017): 'detective_case' → frameVariant:'detective'
 *                            'neutral'         → frameVariant:'neutral'
 */

import { renderArtifactUi } from "./artifact-ui/renderer.js";

export type InverseThinkingArtifactKind = "lesson" | "worksheet" | "quiz" | "drill" | "teacher_only";
export type InverseThinkingFrame = "detective_case" | "neutral";

export interface InverseThinkingRenderCase {
  readonly id: string;
  readonly title: string;
  readonly alias?: string | null;
  readonly disaster: string;
  readonly key_clues: readonly string[];
  readonly safe_zone: string;
  readonly filing_note: string;
  readonly student_task: string;
  readonly teacher_only: {
    readonly rationale: string;
    readonly answer_key: string;
  };
}

export interface InverseThinkingSummaryRow {
  readonly case_id: string;
  readonly trap: string;
  readonly clue: string;
  readonly safe_rule: string;
}

export interface InverseThinkingRenderInput {
  readonly artifactType: InverseThinkingArtifactKind;
  readonly title: string;
  readonly subject: string;
  readonly gradeLevel: string;
  readonly frame: InverseThinkingFrame;
  readonly lang?: string;
  readonly cases: readonly InverseThinkingRenderCase[];
  readonly summaryTable: readonly InverseThinkingSummaryRow[];
  readonly teacherOnly: {
    readonly rationale: string;
    readonly answer_key: string;
  };
}

export async function renderInverseThinkingHtml(
  input: InverseThinkingRenderInput,
): Promise<string> {
  const audience = input.artifactType === "teacher_only" ? "teacher" : "student";
  return renderArtifactUi({
    family: "investigation-folder",
    kind: "inverse-thinking",
    audience,
    data: input,
    lang: input.lang,
  });
}
