import process from "node:process";
import { inspect } from "node:util";

import { renderArtifact } from "./renderer.js";
import type {
  AnswerKeyData,
  ContentComponent,
  DrillData,
  InfographicData,
  LessonData,
  QuizData,
  RecapData,
  WorksheetData,
} from "./contracts/index.js";

type ArtifactRecord = Readonly<Record<string, unknown>>;

const KNOWN_COMPONENT_TYPES = [
  "heading",
  "paragraph",
  "callout",
  "table",
  "stat_grid",
  "pattern_grid",
  "trait_grid",
  "taxonomy_grid",
  "phase_timeline",
  "flow_step",
  "question_card",
  "question_list",
  "concept_map",
  "timeline",
  "alert",
  "vocab_cluster",
  "contrastive_pairs",
  "phrasal_verb_cluster",
  "film_clip_activity",
  "roleplay_script",
  "active_recall_prompt",
  "hw_list",
] as const satisfies readonly ContentComponent["type"][];

type KnownComponentType = (typeof KNOWN_COMPONENT_TYPES)[number];
type MissingComponentType = Exclude<ContentComponent["type"], KnownComponentType>;
const componentRegistryCoversUnion: MissingComponentType extends never ? true : never = true;
const KNOWN_COMPONENT_TYPE_SET: ReadonlySet<string> = new Set(KNOWN_COMPONENT_TYPES);

export class UnknownContentComponentError extends Error {
  readonly componentType: string;
  readonly sectionId: string;

  constructor(componentType: string, sectionId: string) {
    super(`Unknown content component type '${componentType}' in section '${sectionId}'`);
    this.name = "UnknownContentComponentError";
    this.componentType = componentType;
    this.sectionId = sectionId;
  }
}

function asRecord(value: unknown): ArtifactRecord {
  return value !== null && typeof value === "object" ? value as ArtifactRecord : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function asRecordArray(value: unknown): readonly ArtifactRecord[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

export function isContentComponent(value: unknown): value is ContentComponent {
  if (value === null || typeof value !== "object" || !("type" in value)) {
    return false;
  }
  return typeof value.type === "string" && KNOWN_COMPONENT_TYPE_SET.has(value.type);
}

function common(artifact: ArtifactRecord): Pick<LessonData, "title" | "subject" | "gradeLevel" | "theme" | "lang"> {
  const metadata = asRecord(artifact.metadata);
  const accessibility = asRecord(artifact.accessibility);
  return {
    title: asString(artifact.title, "Untitled Teaching Pack"),
    subject: asString(metadata.subject, "General"),
    gradeLevel: asString(metadata.grade_level, asString(metadata.gradeLevel, "Grade")),
    theme: asString(artifact.theme, "default"),
    lang: asString(accessibility.language, "vi"),
  };
}

function sectionId(section: ArtifactRecord, fallback: string): string {
  return asString(section.id, fallback);
}

function preserveComponents(section: ArtifactRecord, fallbackSectionId: string): readonly ContentComponent[] {
  const raw = section.components;
  if (!Array.isArray(raw)) return [];
  return raw.map((component) => parseContentComponent(component, sectionId(section, fallbackSectionId)));
}

function parseContentComponent(component: unknown, sourceSectionId: string): ContentComponent {
  if (isContentComponent(component)) {
    return component;
  }
  const record = asRecord(component);
  const componentType = asString(record.type, inspect(component));
  throw new UnknownContentComponentError(componentType, sourceSectionId);
}

function projectQuestionCardForStudent(component: ContentComponent & { type: "question_card" }): ContentComponent & { type: "question_card" } {
  const { answer: _answer, explain: _explain, wrong_reasons: _wrongReasons, ...studentComponent } = component;
  return studentComponent;
}

function projectComponentForStudent(component: ContentComponent): ContentComponent {
  switch (component.type) {
    case "question_card":
      return projectQuestionCardForStudent(component);
    case "question_list":
      return {
        ...component,
        questions: component.questions.map(projectQuestionCardForStudent),
      };
    case "roleplay_script": {
      const { answer_key: _answerKey, coaching_notes: _coachingNotes, ...studentComponent } = component;
      return studentComponent;
    }
    case "active_recall_prompt": {
      const { reveal_answer: _revealAnswer, teacher_rationale: _teacherRationale, ...studentComponent } = component;
      return studentComponent;
    }
    case "contrastive_pairs":
      return {
        ...component,
        rows: component.rows?.map(({ teacher_rationale: _teacherRationale, ...row }) => row),
      };
    case "heading":
    case "paragraph":
    case "callout":
    case "table":
    case "stat_grid":
    case "pattern_grid":
    case "trait_grid":
    case "taxonomy_grid":
    case "phase_timeline":
    case "flow_step":
    case "concept_map":
    case "timeline":
    case "alert":
    case "vocab_cluster":
    case "phrasal_verb_cluster":
    case "film_clip_activity":
    case "hw_list":
      return component;
    default:
      return assertNeverComponent(component);
  }
}

function assertNeverComponent(component: never): never {
  throw new Error(`Unhandled content component projection: ${inspect(component)}`);
}

function preserveStudentComponents(section: ArtifactRecord, fallbackSectionId: string): readonly ContentComponent[] {
  return preserveComponents(section, fallbackSectionId).map(projectComponentForStudent);
}

function lessonData(artifact: ArtifactRecord): LessonData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  const objectives = sections
    .filter((section) => asString(section.type) === "objective")
    .map((section) => asString(section.content));
  return {
    ...common(artifact),
    objectives,
    sections: sections.map((section, index) => ({
      heading: asString(section.title, `Section ${index + 1}`),
      body: asString(section.content, asString(section.text, "")),
      id: asString(section.id, `section-${index + 1}`),
      time: asString(section.time, ""),
      components: preserveStudentComponents(section, `section-${index + 1}`),
    })),
    hero: {
      eyebrow: asString(artifact.artifact_type, "lesson"),
      lede: asString(asRecord(artifact.metadata).summary, "A structured oh-my-class lesson pack."),
      objectives,
    },
  };
}

function worksheetData(artifact: ArtifactRecord): WorksheetData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    sections: sections.map((section, index) => ({
      title: asString(section.title, `Practice ${index + 1}`),
      questions: asRecordArray(section.questions).length > 0
        ? asRecordArray(section.questions).map((question, questionIndex) => ({
            id: asString(question.id, `w${index + 1}-${questionIndex + 1}`),
            prompt: asString(question.prompt, asString(question.content, "Write your answer.")),
            type: asString(question.type, "short_answer"),
          }))
        : [{
            id: `w${index + 1}-1`,
            prompt: asString(section.content, "Complete this practice task."),
            type: "short_answer",
          }],
    })),
  };
}

function optionList(optionsValue: unknown): { label: string; text: string }[] {
  const options = asRecord(optionsValue);
  const labels = ["A", "B", "C", "D"];
  return labels.map((label) => ({
    label,
    text: asString(options[label], label),
  }));
}

function quizAnswer(section: ArtifactRecord): string {
  return asString(
    section.answer,
    asString(
      section.correct_answer,
      asString(section.correctAnswer, asString(section.correct_option, asString(section.correctOption))),
    ),
  );
}

function quizExplanation(section: ArtifactRecord): string {
  return asString(section.explain, asString(section.explanation, asString(section.rationale)));
}

function quizData(artifact: ArtifactRecord): QuizData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    timeLimit: 10,
    questions: sections.map((section, index) => ({
      id: asString(section.id, `q${index + 1}`),
      prompt: asString(section.prompt, asString(section.content, asString(section.text, "Question"))),
      options: optionList(section.options),
      answer: quizAnswer(section),
      explain: quizExplanation(section),
    })),
  };
}

function drillData(artifact: ArtifactRecord): DrillData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    timeLimit: 10,
    questions: sections.map((section, index) => ({
      id: asString(section.id, `d${index + 1}`),
      prompt: asString(section.prompt, asString(section.content, asString(section.text, "Practice question"))),
      answer: quizAnswer(section),
      type: asString(section.type, "fill") === "question_card" ? "mc" : "fill",
      options: optionList(section.options),
    })),
  };
}

function recapData(artifact: ArtifactRecord): RecapData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    items: sections.map((section, index) => ({
      id: asString(section.id, `recap-${index + 1}`),
      concept: asString(section.title, `Concept ${index + 1}`),
      summary: asString(section.content, asString(section.summary, "Review this concept.")),
    })),
  };
}

function infographicData(artifact: ArtifactRecord): InfographicData {
  const sections = asRecordArray(artifact.sections).filter((section) => section.teacher_only !== true);
  return {
    ...common(artifact),
    sections: sections.map((section, index) => ({
      title: asString(section.title, `Visual ${index + 1}`),
      content: asString(section.content, asString(section.summary, "")),
    })),
  };
}

function answerKeyData(artifact: ArtifactRecord): AnswerKeyData {
  const sections = asRecordArray(artifact.sections);
  return {
    title: common(artifact).title,
    theme: common(artifact).theme,
    accessibility: { language: common(artifact).lang },
    sections: sections.map((section, index) => ({
      id: asString(section.id, `answer-${index + 1}`),
      title: asString(section.title, `Answer ${index + 1}`),
      summary: asString(section.content, asString(section.summary, "")),
      components: [...preserveComponents(section, `answer-${index + 1}`)],
    })),
  };
}

export async function renderAgentArtifact(input: unknown): Promise<string> {
  const artifact = asRecord(input);
  const artifactType = asString(artifact.artifact_type, "lesson");
  switch (artifactType) {
    case "quiz":
      return renderArtifact("quiz", quizData(artifact));
    case "worksheet":
      return renderArtifact("worksheet", worksheetData(artifact));
    case "drill":
      return renderArtifact("drill", drillData(artifact));
    case "recap":
      return renderArtifact("recap", recapData(artifact));
    case "infographic":
      return renderArtifact("infographic", infographicData(artifact));
    case "answer_key":
      return renderArtifact("answer_key", answerKeyData(artifact));
    default:
      return renderArtifact("lesson", lessonData(artifact));
  }
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  return Buffer.concat(chunks).toString("utf8");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const raw = await readStdin();
  const html = await renderAgentArtifact(JSON.parse(raw));
  process.stdout.write(html);
}
