import type { InverseThinkingRenderInput } from "../src/inverse-thinking-renderer.js";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type CorpusCase = Readonly<{
  case_id: string;
  subject: string;
  grade_band: string;
  locale: string;
  pack: Readonly<{
    creative_frame: "auto" | "detective_case" | "courtroom_trial" | "mythbusters_lab" | "survival_guide" | "disaster_report" | "custom";
    cases: InverseThinkingRenderInput["cases"];
    summary_table: InverseThinkingRenderInput["summaryTable"];
    teacher_only: InverseThinkingRenderInput["teacherOnly"];
  }>;
}>;

const currentDir = dirname(fileURLToPath(import.meta.url));
const corpusPath = resolve(currentDir, "../../../tests/fixtures/inverse_thinking/positive/english_grammar.json");
const corpus = JSON.parse(readFileSync(corpusPath, "utf8")) as CorpusCase;

export const inverseThinkingFixture: InverseThinkingRenderInput = {
  artifactType: "lesson",
  title: "Present Perfect Case File",
  subject: corpus.subject,
  gradeLevel: corpus.grade_band,
  frame: corpus.pack.creative_frame === "detective_case" ? "detective_case" : "neutral",
  lang: corpus.locale,
  cases: corpus.pack.cases,
  summaryTable: corpus.pack.summary_table,
  teacherOnly: corpus.pack.teacher_only,
};
